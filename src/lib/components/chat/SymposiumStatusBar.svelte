<script lang="ts">
	import { models } from '$lib/stores';
	import { onMount, onDestroy } from 'svelte';

	export let status: string | null = null;
	export let currentModel: string | null = null;
	export let paused: boolean = false;
	export let interval: number = 30;

	let countdown = 0;
	let countdownInterval: any = null;

	$: modelInfo = currentModel ? $models.find((m) => m.id === currentModel) : null;
	$: modelName = modelInfo?.name || currentModel || 'Unknown';

	// Start countdown when status changes
	$: if (status === null && !paused) {
		startCountdown();
	} else {
		stopCountdown();
	}

	function startCountdown() {
		countdown = interval;
		if (countdownInterval) clearInterval(countdownInterval);

		countdownInterval = setInterval(() => {
			countdown--;
			if (countdown <= 0) {
				countdown = interval;
			}
		}, 1000);
	}

	function stopCountdown() {
		if (countdownInterval) {
			clearInterval(countdownInterval);
			countdownInterval = null;
		}
		countdown = 0;
	}

	onDestroy(() => {
		stopCountdown();
	});
</script>

{#if status || currentModel}
	<div
		class="sticky top-0 z-10 bg-gradient-to-r from-emerald-50 to-blue-50 dark:from-emerald-900/20 dark:to-blue-900/20 border-b border-emerald-200 dark:border-emerald-800 px-4 py-2 shadow-sm"
	>
		<div class="flex items-center justify-between max-w-5xl mx-auto">
			<div class="flex items-center space-x-3">
				{#if modelInfo}
					<img
						src={modelInfo.info?.meta?.profile_image_url ||
							`/api/models/model/profile/image?id=${currentModel}`}
						alt={modelName}
						class="w-8 h-8 rounded-full object-cover ring-2 ring-emerald-400 dark:ring-emerald-600"
					/>
				{:else}
					<div
						class="w-8 h-8 rounded-full bg-emerald-500 dark:bg-emerald-600 flex items-center justify-center"
					>
						<svg class="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"
							/>
						</svg>
					</div>
				{/if}

				<div class="flex flex-col">
					<div class="flex items-center space-x-2">
						<span class="text-sm font-medium text-gray-900 dark:text-gray-100">
							{modelName}
						</span>
						{#if status}
							<span class="flex items-center space-x-1 text-xs text-blue-600 dark:text-blue-400">
								<svg class="w-3 h-3 animate-spin" fill="none" viewBox="0 0 24 24">
									<circle
										class="opacity-25"
										cx="12"
										cy="12"
										r="10"
										stroke="currentColor"
										stroke-width="4"
									></circle>
									<path
										class="opacity-75"
										fill="currentColor"
										d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
									></path>
								</svg>
								<span>{status}</span>
							</span>
						{/if}
					</div>
					{#if paused}
						<span class="text-xs text-amber-600 dark:text-amber-400 font-medium"> ⏸️ Paused </span>
					{:else if countdown > 0 && !status}
						<span class="text-xs text-gray-500 dark:text-gray-400">
							Next response in {countdown}s
						</span>
					{/if}
				</div>
			</div>

			<div class="flex items-center space-x-2">
				{#if paused}
					<span
						class="px-2 py-1 text-xs font-medium bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-200 rounded-full"
					>
						PAUSED
					</span>
				{:else if status}
					<span
						class="px-2 py-1 text-xs font-medium bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-200 rounded-full animate-pulse"
					>
						ACTIVE
					</span>
				{:else}
					<span
						class="px-2 py-1 text-xs font-medium bg-emerald-100 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-200 rounded-full"
					>
						RUNNING
					</span>
				{/if}
			</div>
		</div>
	</div>
{/if}
