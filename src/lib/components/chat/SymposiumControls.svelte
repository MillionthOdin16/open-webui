<script lang="ts">
	import { getContext } from 'svelte';
	import { WEBUI_API_BASE_URL } from '$lib/constants';
	import { toast } from 'svelte-sonner';
	import { symposiumPodcastMode } from '$lib/stores';

	const i18n = getContext('i18n');
	export let chat;

	let paused = false;
	let interval = 30;
	let prompt = '';

	$: if (chat && chat.config) {
		paused = chat.config.paused ?? false;
		interval = chat.config.autonomous_interval ?? 30;
		// Only set prompt if it hasn't been edited locally to avoid overwrite on polling (if any)
		if (prompt === '') prompt = chat.config.prompt ?? '';
	}

	const updateConfig = async () => {
		// Update local chat config immediately to reflect changes
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
				prompt: prompt // Sending prompt too, but backend needs to support it?
			})
		});
		if (!res.ok) {
			toast.error('Failed to update symposium config');
		}
	};
</script>

<div class="p-4 border-t border-gray-200 dark:border-gray-800 bg-gray-50 dark:bg-gray-900">
	<div class="flex items-center justify-between mb-4">
		<div class="text-sm font-medium dark:text-gray-200">{$i18n.t('Controls')}</div>
		<button
			class="px-3 py-1.5 text-xs font-medium rounded-lg transition-colors {paused
				? 'bg-emerald-100 text-emerald-800 hover:bg-emerald-200 dark:bg-emerald-900/30 dark:text-emerald-200 dark:hover:bg-emerald-900/50'
				: 'bg-amber-100 text-amber-800 hover:bg-amber-200 dark:bg-amber-900/30 dark:text-amber-200 dark:hover:bg-amber-900/50'}"
			on:click={() => {
				paused = !paused;
				updateConfig();
			}}
		>
			{paused ? $i18n.t('Resume Loop') : $i18n.t('Pause Loop')}
		</button>
	</div>
	<div class="space-y-3">
		<div>
			<div class="text-xs text-gray-500 dark:text-gray-400 mb-1">
				{$i18n.t('System Context')}
			</div>
			<textarea
				class="w-full h-20 rounded-lg text-xs bg-gray-100 dark:bg-gray-800 border-none p-2 resize-none focus:ring-1 focus:ring-emerald-500 outline-none"
				bind:value={prompt}
				on:change={updateConfig}
			/>
		</div>

		<div class="flex justify-between text-xs text-gray-500 dark:text-gray-400">
			<span>{$i18n.t('Response Interval')}</span>
			<span class="font-mono">{interval}s</span>
		</div>
		<input
			type="range"
			min="5"
			max="300"
			step="5"
			class="w-full h-1.5 bg-gray-200 rounded-lg appearance-none cursor-pointer dark:bg-gray-700 accent-emerald-600 hover:accent-emerald-500"
			bind:value={interval}
			on:change={updateConfig}
		/>
	</div>

	<div class="flex items-center justify-between mt-4">
		<div class="text-xs text-gray-500 dark:text-gray-400">{$i18n.t('Podcast Mode')}</div>
		<button
			class="px-2 py-1 text-xs font-medium rounded-lg transition-colors {$symposiumPodcastMode
				? 'bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-200'
				: 'bg-gray-200 text-gray-800 dark:bg-gray-800 dark:text-gray-300'}"
			on:click={() => symposiumPodcastMode.update((v) => !v)}
		>
			{$symposiumPodcastMode ? $i18n.t('ON') : $i18n.t('OFF')}
		</button>
	</div>
</div>
