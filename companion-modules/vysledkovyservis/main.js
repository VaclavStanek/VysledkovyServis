// Companion module for Výsledkový servis – drives the local overlay over the same
// HTTP API the Stream Deck plugin uses (/control to act, /status for live feedback).
// @companion-module/base v2 (Companion 4.x): the host instantiates the default export,
// so the module exports the class instead of calling runEntrypoint (removed in v2).
import { InstanceBase, InstanceStatus, combineRgb } from '@companion-module/base'

const RED = combineRgb(245, 37, 37)
const GREEN = combineRgb(46, 158, 79)
const WHITE = combineRgb(255, 255, 255)

const EMPTY_STATUS = {
	ok: false,
	is_running: false,
	view: 'none',
	category: '',
	discipline: '',
	page: '1',
	page_count: 1,
	auto_paging: true,
	categories: [],
	disciplines: [],
	nameplate_on: false,
	nameplate_name: '',
}

class VysledkovyServisInstance extends InstanceBase {
	async init(config) {
		this.config = config
		this.state = { ...EMPTY_STATUS }
		this.updateStatus(InstanceStatus.Connecting)

		this.initActions()
		this.initFeedbacks()
		this.initVariables()
		this.startPolling()
	}

	async destroy() {
		if (this.pollTimer) clearInterval(this.pollTimer)
	}

	async configUpdated(config) {
		this.config = config
		this.startPolling()
	}

	getConfigFields() {
		return [
			{
				type: 'static-text',
				id: 'info',
				width: 12,
				label: 'Výsledkový servis',
				value: 'Ovládá overlay přes lokální HTTP API aplikace. Appka musí běžet.',
			},
			{
				type: 'textinput',
				id: 'host',
				label: 'Adresa aplikace (host:port)',
				width: 8,
				default: '127.0.0.1:5100',
				tooltip: 'Nativní appka: 127.0.0.1:5100. Dev režim: 127.0.0.1:5000.',
			},
		]
	}

	baseUrl() {
		const host = (this.config?.host || '127.0.0.1:5100').replace(/^https?:\/\//, '').replace(/\/$/, '')
		return `http://${host}`
	}

	async fetchStatus() {
		const res = await fetch(`${this.baseUrl()}/status`)
		return res.json()
	}

	// Next/previous item in a list, wrapping – mirrors the server's cycle_value so the
	// "next/prev" variables can preview the value a press will switch to.
	cycle(list, current, dir) {
		if (!Array.isArray(list) || !list.length) return current
		let i = list.indexOf(current)
		if (i < 0) i = 0
		i = (i + (dir === 'next' ? 1 : -1) + list.length) % list.length
		return list[i]
	}

	startPolling() {
		if (this.pollTimer) clearInterval(this.pollTimer)
		const poll = async () => {
			try {
				this.state = await this.fetchStatus()
				this.updateStatus(InstanceStatus.Ok)
			} catch (e) {
				this.state = { ...EMPTY_STATUS }
				this.updateStatus(InstanceStatus.ConnectionFailure, 'Aplikace neběží nebo špatná adresa?')
			}
			this.updateVariables()
			this.checkFeedbacks('view_active', 'is_running', 'nameplate_active')
		}
		poll()
		this.pollTimer = setInterval(poll, 1000)
	}

	// Send a control command, then refresh state/feedback right away (no wait for poll)
	async send(query, path = '/control') {
		try {
			const res = await fetch(`${this.baseUrl()}${path}${query ? '?' + query : ''}`, { method: 'POST' })
			const data = await res.json()
			if (path === '/control') {
				this.state = data
				this.updateStatus(InstanceStatus.Ok)
				this.updateVariables()
				this.checkFeedbacks('view_active', 'is_running', 'nameplate_active')
			} else {
				this.log(data.ok ? 'info' : 'error', data.message || '')
			}
		} catch (e) {
			this.log('error', 'HTTP požadavek selhal: ' + e.message)
			this.updateStatus(InstanceStatus.ConnectionFailure)
		}
	}

	initActions() {
		const simple = (name, query) => ({ name, options: [], callback: () => this.send(query) })
		this.setActionDefinitions({
			view_results: simple('Pohled: Výsledková tabulka', 'view=results'),
			view_racers: simple('Pohled: Lišta závodníků', 'view=racers'),
			view_total: simple('Pohled: Celkové výsledky', 'view=total'),
			category_next: simple('Kategorie: další', 'category=next'),
			category_prev: simple('Kategorie: předchozí', 'category=prev'),
			discipline_next: simple('Disciplína: další', 'discipline=next'),
			discipline_prev: simple('Disciplína: předchozí', 'discipline=prev'),
			page_next: simple('Strana: další', 'page=next'),
			page_prev: simple('Strana: předchozí', 'page=prev'),
			broadcast_start: simple('Vysílání: spustit', 'action=start'),
			broadcast_stop: simple('Vysílání: zastavit', 'action=stop'),
			broadcast_toggle: {
				name: 'Vysílání: přepnout (start/stop)',
				options: [],
				callback: () => this.send(this.state?.is_running ? 'action=stop' : 'action=start'),
			},
			slowmo_replay: {
				name: 'DaVinci: Slowmo replay (50 %, klip pod playhead)',
				options: [],
				callback: () => this.send('', '/replay'),
			},
			page_cycle: {
				name: 'Strana: cycle (1→2→…→AUTO→1→…)',
				options: [],
				callback: () => this.send('page=cycle'),
			},
			page_auto: simple('Strana: přepnout na AUTO', 'page=auto'),
			race_load: {
				name: 'Načíst a spustit závod',
				options: [
					{ type: 'textinput', id: 'race', label: 'Číslo závodu (z hasicovo.cz)', default: '' },
				],
				callback: (ev) => this.send(`race=${encodeURIComponent(ev.options.race || '')}&action=start`),
			},
			nameplate_show: simple('Jmenovka: zobrazit', 'nameplate=show'),
			nameplate_hide: simple('Jmenovka: skrýt', 'nameplate=hide'),
			nameplate_toggle: simple('Jmenovka: přepnout (zobrazit/skrýt)', 'nameplate=toggle'),
		})
	}

	initFeedbacks() {
		this.setFeedbackDefinitions({
			view_active: {
				type: 'boolean',
				name: 'Pohled je aktivní',
				description: 'Zvýrazní tlačítko, když je daný pohled v overlayi aktivní',
				defaultStyle: { bgcolor: RED, color: WHITE },
				options: [
					{
						type: 'dropdown',
						id: 'view',
						label: 'Pohled',
						default: 'results',
						choices: [
							{ id: 'results', label: 'Výsledková tabulka' },
							{ id: 'racers', label: 'Lišta závodníků' },
							{ id: 'total', label: 'Celkové výsledky' },
						],
					},
				],
				callback: (fb) => this.state?.view === fb.options.view,
			},
			is_running: {
				type: 'boolean',
				name: 'Vysílá data',
				description: 'Zvýrazní tlačítko, když overlay právě vysílá',
				defaultStyle: { bgcolor: GREEN, color: WHITE },
				options: [],
				callback: () => !!this.state?.is_running,
			},
			nameplate_active: {
				type: 'boolean',
				name: 'Jmenovka je na vysílání',
				description: 'Zvýrazní tlačítko, když je jmenovka právě promítaná',
				defaultStyle: { bgcolor: RED, color: WHITE },
				options: [],
				callback: () => !!this.state?.nameplate_on,
			},
		})
	}

	initVariables() {
		this.setVariableDefinitions({
			view:            { name: 'Aktuální pohled' },
			is_running:      { name: 'Vysílá (true/false)' },
			category:        { name: 'Aktuální kategorie' },
			category_next:   { name: 'Další kategorie (na kterou přepne)' },
			category_prev:   { name: 'Předchozí kategorie' },
			discipline:      { name: 'Aktuální disciplína' },
			discipline_next: { name: 'Další disciplína' },
			discipline_prev: { name: 'Předchozí disciplína' },
			page:            { name: 'Aktuální strana (číslo nebo AUTO)' },
			page_next:       { name: 'Další strana (číslo)' },
			page_prev:       { name: 'Předchozí strana (číslo)' },
			page_count:      { name: 'Celkový počet stran' },
			auto_paging:     { name: 'Automatické stránkování (true/false)' },
			nameplate_on:    { name: 'Jmenovka na vysílání (true/false)' },
			nameplate_name:  { name: 'Jmenovka: text/jméno' },
		})
	}

	updateVariables() {
		const s = this.state || EMPTY_STATUS
		const isAuto = s.auto_paging === true || s.page === 'AUTO'
		const pageNum = isAuto ? 1 : (parseInt(s.page || '1', 10) || 1)
		const pageCount = s.page_count || 1
		this.setVariableValues({
			view: s.view || 'none',
			is_running: s.is_running ? 'true' : 'false',
			category: s.category || '–',
			category_next: this.cycle(s.categories, s.category, 'next') || '–',
			category_prev: this.cycle(s.categories, s.category, 'prev') || '–',
			discipline: s.discipline || '–',
			discipline_next: this.cycle(s.disciplines, s.discipline, 'next') || '–',
			discipline_prev: this.cycle(s.disciplines, s.discipline, 'prev') || '–',
			page: isAuto ? 'AUTO' : String(pageNum),
			page_next: String(pageNum + 1),
			page_prev: String(Math.max(1, pageNum - 1)),
			page_count: String(pageCount),
			auto_paging: isAuto ? 'true' : 'false',
			nameplate_on: s.nameplate_on ? 'true' : 'false',
			nameplate_name: s.nameplate_name || '–',
		})
	}

}

export default VysledkovyServisInstance
