<script lang="ts">
	import { getContext, onMount, onDestroy } from 'svelte';
	import { WEBUI_API_BASE_URL } from '$lib/constants';
	import { toast } from 'svelte-sonner';
	import { symposiumPodcastMode, socket } from '$lib/stores';
	import {
		exportSymposiumConfig,
		downloadSymposiumConfig,
		importSymposiumConfig
	} from '$lib/utils/symposium';
	import Tooltip from '../common/Tooltip.svelte';

	const i18n = getContext('i18n');
	export let chat;

	let paused = false;
	let interval = 30;
	let contextLimit = 20;
	let prompt = '';
	let narratorText = '';
	let fileInput: HTMLInputElement;
	let showPromptEditor = false;
	let showNarratorInput = false;
	let showAdvanced = false;
	let isSymposiumActive = false;
	let lastHeartbeat = 0;

	$: if (chat && chat.config) {
		paused = chat.config.paused ?? false;
		interval = chat.config.autonomous_interval ?? 30;
		contextLimit = chat.config.context_limit ?? 20;
		if (prompt === '') prompt = chat.config.prompt ?? '';
	}

	// Check symposium status
	const checkSymposiumStatus = async () => {
		try {
			const res = await fetch(`${WEBUI_API_BASE_URL}/chats/${chat.id}/symposium/status`, {
				headers: { authorization: `Bearer ${localStorage.token}` }
			});
			if (res.ok) {
				const data = await res.json();
				isSymposiumActive = data.active;
				lastHeartbeat = Date.now();
			}
		} catch (e) {
			console.error('Error checking symposium status:', e);
		}
	};

	// Resume symposium if it's not running
	const resumeSymposium = async () => {
		try {
			const res = await fetch(`${WEBUI_API_BASE_URL}/chats/${chat.id}/symposium/resume`, {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					authorization: `Bearer ${localStorage.token}`
				}
			});
			if (res.ok) {
				isSymposiumActive = true;
				// If we are resuming a dead process but it was "paused" in config, unpause it
				if (paused) {
					paused = false;
					await updateConfig();
				}
				toast.success($i18n.t('Symposium resumed'));
			} else {
				toast.error($i18n.t('Failed to resume symposium'));
			}
		} catch (e) {
			toast.error($i18n.t('Network error'));
		}
	};

	// Send narrator/splice message
	const sendNarratorMessage = async () => {
		if (!narratorText.trim()) return;
		
		try {
			const res = await fetch(`${WEBUI_API_BASE_URL}/chats/${chat.id}/splice`, {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					authorization: `Bearer ${localStorage.token}`
				},
				body: JSON.stringify({ content: narratorText })
			});
			if (res.ok) {
				toast.success($i18n.t('Narrator event injected'));
				narratorText = '';
				showNarratorInput = false;
			} else {
				toast.error($i18n.t('Failed to inject narrator event'));
			}
		} catch (e) {
			toast.error($i18n.t('Network error'));
		}
	};

	const updateConfig = async () => {
		chat.config.paused = paused;
		chat.config.autonomous_interval = interval;
		chat.config.context_limit = contextLimit;
		chat.config.prompt = prompt;

		const res = await fetch(`${WEBUI_API_BASE_URL}/chats/${chat.id}/symposium/config`, {
			method: 'PUT',
			headers: {
				'Content-Type': 'application/json',
				authorization: `Bearer ${localStorage.token}`
			},
			body: JSON.stringify({
				paused: paused,
				interval: interval,
				context_limit: contextLimit,
				prompt: prompt
			})
		});
		if (!res.ok) {
			toast.error($i18n.t('Failed to update symposium config'));
		}
	};

	const onSymposiumStatus = (data: any) => {
		if (data.chat_id === chat.id) {
			lastHeartbeat = Date.now();
			isSymposiumActive = true;
		}
	};

	const onSymposiumStopped = (data: any) => {
		if (data.chat_id === chat.id) {
			isSymposiumActive = false;
		}
	};

	onMount(() => {
		checkSymposiumStatus();
		$socket?.on('symposium:status', onSymposiumStatus);
		$socket?.on('symposium:stopped', onSymposiumStopped);
	});

	onDestroy(() => {
		$socket?.off('symposium:status', onSymposiumStatus);
		$socket?.off('symposium:stopped', onSymposiumStopped);
	});

	const handleExport = () => {
		const config = exportSymposiumConfig(chat);
		downloadSymposiumConfig(config);
		toast.success($i18n.t('Configuration exported successfully'));
	};

	const handleImportClick = () => {
		fileInput.click();
	};

	const handleImportFile = async (event: Event) => {
		const target = event.target as HTMLInputElement;
		const file = target.files?.[0];
		if (!file) return;

		try {
			const config = await importSymposiumConfig(file);
			prompt = config.config.prompt;
			interval = config.config.autonomous_interval;
			chat.config.prompt = config.config.prompt;
			chat.config.autonomous_interval = config.config.autonomous_interval;
			chat.config.context_limit = config.config.context_limit;
			await updateConfig();
			toast.success($i18n.t('Configuration imported successfully'));
		} catch (error) {
			toast.error(error.message || $i18n.t('Failed to import configuration'));
		}
		target.value = '';
	};
</script>

<div class="p-4 bg-gradient-to-b from-gray-50 to-gray-100 dark:from-gray-900 dark:to-gray-950">
	<!-- Status Indicator -->
	{#if !isSymposiumActive}
		<div class="mb-3 p-3 bg-red-50 dark:bg-red-900/20 rounded-xl border border-red-200 dark:border-red-800 animate-pulse">
			<div class="flex items-center gap-2 text-red-700 dark:text-red-300">
				<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="w-5 h-5">
					<path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a.75.75 0 000 1.5h.253a.25.25 0 01.244.304l-.459 2.066A1.75 1.75 0 0010.747 15H11a.75.75 0 000-1.5h-.253a.25.25 0 01-.244-.304l.459-2.066A1.75 1.75 0 009.253 9H9z" clip-rule="evenodd" />
				</svg>
				<span class="text-sm font-medium">{$i18n.t('Symposium process stopped')}</span>
			</div>
			<button
				class="mt-2 w-full py-2 px-3 bg-red-500 hover:bg-red-600 text-white text-sm rounded-lg font-medium transition-colors"
				on:click={resumeSymposium}
			>
				{$i18n.t('Restart Symposium')}
			</button>
		</div>
	{/if}

	<!-- Main Control Button -->
	<button
		class="w-full py-3 px-4 rounded-xl font-medium text-sm transition-all flex items-center justify-center gap-2
			{paused
				? 'bg-gradient-to-r from-emerald-500 to-teal-500 hover:from-emerald-600 hover:to-teal-600 text-white shadow-lg shadow-emerald-500/25'
				: 'bg-gradient-to-r from-amber-500 to-orange-500 hover:from-amber-600 hover:to-orange-600 text-white shadow-lg shadow-amber-500/25'}"
		on:click={() => {
			paused = !paused;
			updateConfig();
		}}
		disabled={!isSymposiumActive}
	>
		{#if paused}
			<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="w-5 h-5">
				<path d="M6.3 2.841A1.5 1.5 0 004 4.11V15.89a1.5 1.5 0 002.3 1.269l9.344-5.89a1.5 1.5 0 000-2.538L6.3 2.84z" />
			</svg>
			{$i18n.t('Resume Symposium')}
		{:else}
			<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="w-5 h-5">
				<path d="M5.75 3a.75.75 0 00-.75.75v12.5c0 .414.336.75.75.75h1.5a.75.75 0 00.75-.75V3.75A.75.75 0 007.25 3h-1.5zM12.75 3a.75.75 0 00-.75.75v12.5c0 .414.336.75.75.75h1.5a.75.75 0 00.75-.75V3.75a.75.75 0 00-.75-.75h-1.5z" />
			</svg>
			{$i18n.t('Pause Symposium')}
		{/if}
	</button>

	<!-- Narrator/Splice Input -->
	<div class="mt-3">
		<button
			class="w-full flex items-center justify-between p-3 bg-gradient-to-r from-purple-50 to-pink-50 dark:from-purple-900/20 dark:to-pink-900/20 rounded-xl border border-purple-200 dark:border-purple-800 hover:border-purple-300 dark:hover:border-purple-700 transition-colors"
			on:click={() => showNarratorInput = !showNarratorInput}
		>
			<div class="flex items-center gap-2">
				<span class="text-lg">📢</span>
				<span class="text-sm font-medium text-purple-700 dark:text-purple-300">{$i18n.t('Narrator Event')}</span>
			</div>
			<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="w-4 h-4 text-purple-400 transition-transform {showNarratorInput ? 'rotate-180' : ''}">
				<path fill-rule="evenodd" d="M5.23 7.21a.75.75 0 011.06.02L10 11.168l3.71-3.938a.75.75 0 111.08 1.04l-4.25 4.5a.75.75 0 01-1.08 0l-4.25-4.5a.75.75 0 01.02-1.06z" clip-rule="evenodd" />
			</svg>
		</button>
		
		{#if showNarratorInput}
			<div class="mt-2 p-3 bg-white dark:bg-gray-800 rounded-xl border border-purple-200 dark:border-purple-700">
				<p class="text-xs text-gray-500 dark:text-gray-400 mb-2">{$i18n.t('Inject a narrator event into the conversation (e.g., "A dragon suddenly appears")')}</p>
				<textarea
					class="w-full h-20 text-sm bg-gray-50 dark:bg-gray-900 rounded-lg p-2 border border-gray-200 dark:border-gray-700 resize-none focus:ring-2 focus:ring-purple-500 focus:border-purple-500 outline-none"
					placeholder={$i18n.t('Enter narrator text...')}
					bind:value={narratorText}
				></textarea>
				<button
					class="mt-2 w-full py-2 px-3 bg-purple-500 hover:bg-purple-600 text-white text-sm rounded-lg font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
					on:click={sendNarratorMessage}
					disabled={!narratorText.trim()}
				>
					{$i18n.t('Inject Event')}
				</button>
			</div>
		{/if}
	</div>

	<!-- Quick Settings Row -->
	<div class="mt-4 grid grid-cols-2 gap-3">
		<!-- Interval Control -->
		<div class="bg-white dark:bg-gray-800 rounded-xl p-3 border border-gray-200 dark:border-gray-700">
			<div class="flex items-center justify-between mb-2">
				<span class="text-xs font-medium text-gray-500 dark:text-gray-400">{$i18n.t('Interval')}</span>
				<span class="text-sm font-bold text-emerald-600 dark:text-emerald-400">{interval}s</span>
			</div>
			<input
				type="range"
				min="10"
				max="120"
				step="5"
				class="w-full h-1.5 bg-gray-200 rounded-lg appearance-none cursor-pointer dark:bg-gray-700 accent-emerald-500"
				bind:value={interval}
				on:change={updateConfig}
			/>
		</div>

		<!-- Podcast Mode Toggle -->
		<div class="bg-white dark:bg-gray-800 rounded-xl p-3 border border-gray-200 dark:border-gray-700">
			<div class="flex items-center justify-between mb-2">
				<span class="text-xs font-medium text-gray-500 dark:text-gray-400">{$i18n.t('Podcast')}</span>
				<span class="text-lg">🎙️</span>
			</div>
			<button
				class="w-full py-1.5 text-xs font-medium rounded-lg transition-all
					{$symposiumPodcastMode
						? 'bg-purple-100 text-purple-700 dark:bg-purple-900/50 dark:text-purple-300'
						: 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400'}"
				on:click={() => symposiumPodcastMode.update((v) => !v)}
			>
				{$symposiumPodcastMode ? $i18n.t('Enabled') : $i18n.t('Disabled')}
			</button>
		</div>
	</div>

	<!-- Context Limit Control -->
	<div class="mt-3 bg-white dark:bg-gray-800 rounded-xl p-3 border border-gray-200 dark:border-gray-700">
		<div class="flex items-center justify-between mb-2">
			<div class="flex items-center gap-1.5">
				<span class="text-xs font-medium text-gray-500 dark:text-gray-400">{$i18n.t('Memory (messages)')}</span>
				<Tooltip content={$i18n.t('Number of past messages each AI can see. Higher = better context but slower.')}>
					<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="w-3.5 h-3.5 text-gray-400">
						<path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zM8.94 6.94a.75.75 0 11-1.061-1.061 3 3 0 112.871 5.026v.345a.75.75 0 01-1.5 0v-.5c0-.72.57-1.172 1.081-1.287A1.5 1.5 0 108.94 6.94zM10 15a1 1 0 100-2 1 1 0 000 2z" clip-rule="evenodd" />
					</svg>
				</Tooltip>
			</div>
			<span class="text-sm font-bold text-blue-600 dark:text-blue-400">{contextLimit}</span>
		</div>
		<input
			type="range"
			min="5"
			max="50"
			step="5"
			class="w-full h-1.5 bg-gray-200 rounded-lg appearance-none cursor-pointer dark:bg-gray-700 accent-blue-500"
			bind:value={contextLimit}
			on:change={updateConfig}
		/>
		<div class="flex justify-between text-xs text-gray-400 mt-1">
			<span>{$i18n.t('Fast')}</span>
			<span>{$i18n.t('More context')}</span>
		</div>
	</div>

	<!-- Topic/Prompt Section -->
	<div class="mt-4">
		<button
			class="w-full flex items-center justify-between p-3 bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 hover:border-emerald-300 dark:hover:border-emerald-700 transition-colors"
			on:click={() => showPromptEditor = !showPromptEditor}
		>
			<div class="flex items-center gap-2">
				<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="w-4 h-4 text-gray-400">
					<path fill-rule="evenodd" d="M4.5 2A1.5 1.5 0 003 3.5v13A1.5 1.5 0 004.5 18h11a1.5 1.5 0 001.5-1.5V7.621a1.5 1.5 0 00-.44-1.06l-4.12-4.122A1.5 1.5 0 0011.378 2H4.5z" clip-rule="evenodd" />
				</svg>
				<span class="text-sm font-medium text-gray-700 dark:text-gray-300">{$i18n.t('Topic & Context')}</span>
			</div>
			<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="w-4 h-4 text-gray-400 transition-transform {showPromptEditor ? 'rotate-180' : ''}">
				<path fill-rule="evenodd" d="M5.23 7.21a.75.75 0 011.06.02L10 11.168l3.71-3.938a.75.75 0 111.08 1.04l-4.25 4.5a.75.75 0 01-1.08 0l-4.25-4.5a.75.75 0 01.02-1.06z" clip-rule="evenodd" />
			</svg>
		</button>
		
		{#if showPromptEditor}
			<div class="mt-2 p-3 bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700">
				<textarea
					class="w-full h-24 text-xs bg-gray-50 dark:bg-gray-900 rounded-lg p-2 border border-gray-200 dark:border-gray-700 resize-none focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 outline-none"
					placeholder={$i18n.t('Enter the topic and context for discussion...')}
					bind:value={prompt}
					on:change={updateConfig}
				></textarea>
			</div>
		{/if}
	</div>

	<!-- Action Buttons -->
	<div class="mt-4 flex items-center justify-between">
		<div class="text-xs text-gray-500 dark:text-gray-400">{$i18n.t('Configuration')}</div>
		<div class="flex gap-2">
			<Tooltip content={$i18n.t('Export config')}>
				<button
					class="p-2 rounded-lg bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
					on:click={handleExport}
				>
					<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="w-4 h-4 text-gray-500">
						<path d="M10.75 2.75a.75.75 0 00-1.5 0v8.614L6.295 8.235a.75.75 0 10-1.09 1.03l4.25 4.5a.75.75 0 001.09 0l4.25-4.5a.75.75 0 00-1.09-1.03l-2.955 3.129V2.75z" />
						<path d="M3.5 12.75a.75.75 0 00-1.5 0v2.5A2.75 2.75 0 004.75 18h10.5A2.75 2.75 0 0018 15.25v-2.5a.75.75 0 00-1.5 0v2.5c0 .69-.56 1.25-1.25 1.25H4.75c-.69 0-1.25-.56-1.25-1.25v-2.5z" />
					</svg>
				</button>
			</Tooltip>
			<Tooltip content={$i18n.t('Import config')}>
				<button
					class="p-2 rounded-lg bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
					on:click={handleImportClick}
				>
					<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="w-4 h-4 text-gray-500">
						<path d="M9.25 13.25a.75.75 0 001.5 0V4.636l2.955 3.129a.75.75 0 001.09-1.03l-4.25-4.5a.75.75 0 00-1.09 0l-4.25 4.5a.75.75 0 101.09 1.03L9.25 4.636v8.614z" />
						<path d="M3.5 12.75a.75.75 0 00-1.5 0v2.5A2.75 2.75 0 004.75 18h10.5A2.75 2.75 0 0018 15.25v-2.5a.75.75 0 00-1.5 0v2.5c0 .69-.56 1.25-1.25 1.25H4.75c-.69 0-1.25-.56-1.25-1.25v-2.5z" />
					</svg>
				</button>
			</Tooltip>
		</div>
	</div>

	<input
		type="file"
		accept=".json"
		class="hidden"
		bind:this={fileInput}
		on:change={handleImportFile}
	/>
</div>
