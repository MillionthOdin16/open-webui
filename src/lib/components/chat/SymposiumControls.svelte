<script lang="ts">
	import { getContext } from 'svelte';
	import { WEBUI_API_BASE_URL } from '$lib/constants';
	import { toast } from 'svelte-sonner';
	import { symposiumPodcastMode } from '$lib/stores';
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
	let prompt = '';
	let fileInput: HTMLInputElement;
	let showPromptEditor = false;

	$: if (chat && chat.config) {
		paused = chat.config.paused ?? false;
		interval = chat.config.autonomous_interval ?? 30;
		if (prompt === '') prompt = chat.config.prompt ?? '';
	}

	const updateConfig = async () => {
		chat.config.paused = paused;
		chat.config.autonomous_interval = interval;
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
				prompt: prompt
			})
		});
		if (!res.ok) {
			toast.error($i18n.t('Failed to update symposium config'));
		}
	};

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
