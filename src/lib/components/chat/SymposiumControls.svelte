<script lang="ts">
	import { getContext } from 'svelte';
	import { WEBUI_API_BASE_URL } from '$lib/constants';
	import { toast } from 'svelte-sonner';

	const i18n = getContext('i18n');
	export let chat;

	let paused = false;
	let interval = 30;

	$: if (chat && chat.config) {
		paused = chat.config.paused ?? false;
		interval = chat.config.autonomous_interval ?? 30;
	}

	const updateConfig = async () => {
		const res = await fetch(`${WEBUI_API_BASE_URL}/chats/${chat.id}/symposium/config`, {
			method: 'PUT',
			headers: {
				'Content-Type': 'application/json',
				authorization: `Bearer ${localStorage.token}`
			},
			body: JSON.stringify({
				paused: paused,
				interval: interval
			})
		});
		if (!res.ok) {
			toast.error('Failed to update symposium config');
		} else {
			// Update local chat config immediately to reflect changes
			chat.config.paused = paused;
			chat.config.autonomous_interval = interval;
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
</div>
