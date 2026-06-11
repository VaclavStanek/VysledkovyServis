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
	categories: [],
	disciplines: [],
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

	// --- HTTP helpers (Node 22 provides global fetch) ---
	async control(query) {
		const res = await fetch(`${this.baseUrl()}/control?${query}`)
		return res.json()
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
			this.checkFeedbacks('view_active', 'is_running')
		}
		poll()
		this.pollTimer = setInterval(poll, 1000)
	}

	// Send a control command, then refresh state/feedback right away (no wait for poll)
	async send(query) {
		try {
			this.state = await this.control(query)
			this.updateStatus(InstanceStatus.Ok)
			this.updateVariables()
			this.checkFeedbacks('view_active', 'is_running')
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
			race_load: {
				name: 'Načíst a spustit závod',
				options: [
					{ type: 'textinput', id: 'race', label: 'Číslo závodu (z hasicovo.cz)', default: '' },
				],
				callback: (ev) => this.send(`race=${encodeURIComponent(ev.options.race || '')}&action=start`),
			},
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
		})
	}

	initVariables() {
		this.setVariableDefinitions([
			{ variableId: 'view', name: 'Aktuální pohled' },
			{ variableId: 'is_running', name: 'Vysílá (true/false)' },
			{ variableId: 'category', name: 'Aktuální kategorie' },
			{ variableId: 'category_next', name: 'Další kategorie (na kterou přepne)' },
			{ variableId: 'category_prev', name: 'Předchozí kategorie' },
			{ variableId: 'discipline', name: 'Aktuální disciplína' },
			{ variableId: 'discipline_next', name: 'Další disciplína' },
			{ variableId: 'discipline_prev', name: 'Předchozí disciplína' },
			{ variableId: 'page', name: 'Aktuální strana' },
			{ variableId: 'page_next', name: 'Další strana' },
			{ variableId: 'page_prev', name: 'Předchozí strana' },
		])
	}

	updateVariables() {
		const s = this.state || EMPTY_STATUS
		const page = parseInt(s.page || '1', 10) || 1
		this.setVariableValues({
			view: s.view || 'none',
			is_running: s.is_running ? 'true' : 'false',
			category: s.category || '–',
			category_next: this.cycle(s.categories, s.category, 'next') || '–',
			category_prev: this.cycle(s.categories, s.category, 'prev') || '–',
			discipline: s.discipline || '–',
			discipline_next: this.cycle(s.disciplines, s.discipline, 'next') || '–',
			discipline_prev: this.cycle(s.disciplines, s.discipline, 'prev') || '–',
			page: String(page),
			page_next: String(page + 1),
			page_prev: String(Math.max(1, page - 1)),
		})
	}

}

export default VysledkovyServisInstance
