<script lang="ts">
	import { models, socket } from '$lib/stores';
	import { onMount, onDestroy, getContext } from 'svelte';
	import { WEBUI_API_BASE_URL } from '$lib/constants';
	import { fade, slide } from 'svelte/transition';

	const i18n = getContext('i18n');

	export let chatId: string = '';
	export let status: string | null = null;
	export let currentModel: string | null = null;
	export let paused: boolean = false;
	export let interval: number = 30;
	export let participants: string[] = [];

	let countdown = 0;
	let countdownInterval: ReturnType<typeof setInterval> | null = null;
	let expanded = false;
	let botStates: Record<string, string> = {};

	$: modelInfo = currentModel ? $models.find((m) => m.id === currentModel) : null;
	$: modelName = modelInfo?.name || currentModel?.split('/').pop() || 'AI';

	// Get all participant info
	$: participantModels = participants.map(id => {
		const model = $models.find(m => m.id === id);
		return {
			id,
			name: model?.name || id.split('/').pop() || id,
			image: model?.info?.meta?.profile_image_url || `${WEBUI_API_BASE_URL}/models/model/profile/image?id=${encodeURIComponent(id)}`,
			state: botStates[id] || 'active'
		};
	});

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

	const onBotStateChange = (data: any) => {
		if (data.chat_id === chatId) {
			botStates[data.model_id] = data.state;
			botStates = botStates;
		}
	};

	onMount(() => {
		$socket?.on('symposium:bot_state', onBotStateChange);
	});

	onDestroy(() => {
		stopCountdown();
		$socket?.off('symposium:bot_state', onBotStateChange);
	});

	const getStateIcon = (state: string) => {
		switch (state) {
			case 'speaking': return '🎤';
			case 'listening': return '👂';
			case 'muted': return '🔇';
			default: return '💬';
		}
	};

	const getStateColor = (state: string) => {
		switch (state) {
			case 'speaking': return 'ring-emerald-500 bg-emerald-500';
			case 'listening': return 'ring-amber-500 bg-amber-500';
			case 'muted': return 'ring-gray-400 bg-gray-400';
			default: return 'ring-blue-500 bg-blue-500';
		}
	};
</script>

{#if participants.length > 0}
	<div 
		class="sticky top-0 z-20 backdrop-blur-xl bg-gradient-to-r from-emerald-500/10 via-teal-500/10 to-cyan-500/10 border-b border-emerald-200/50 dark:border-emerald-800/50"
		transition:slide={{ duration: 200 }}
	>
		<!-- Main Bar -->
		<div class="px-4 py-2">
			<div class="flex items-center justify-between max-w-5xl mx-auto">
				<!-- Left: Current Speaker / Status -->
				<div class="flex items-center gap-3">
					{#if status && currentModel}
						<!-- Speaking Animation -->
						<div class="relative">
							<img
								src={modelInfo?.info?.meta?.profile_image_url || `${WEBUI_API_BASE_URL}/models/model/profile/image?id=${encodeURIComponent(currentModel)}`}
								alt={modelName}
								class="w-10 h-10 rounded-full object-cover ring-2 ring-emerald-500 ring-offset-2 ring-offset-white dark:ring-offset-gray-900"
							/>
							<!-- Speaking Waves -->
							<div class="absolute -right-1 -bottom-1 w-5 h-5 bg-emerald-500 rounded-full flex items-center justify-center">
								<div class="flex gap-0.5">
									<div class="w-0.5 h-2 bg-white rounded-full animate-pulse" style="animation-delay: 0s;"></div>
									<div class="w-0.5 h-3 bg-white rounded-full animate-pulse" style="animation-delay: 0.15s;"></div>
									<div class="w-0.5 h-2 bg-white rounded-full animate-pulse" style="animation-delay: 0.3s;"></div>
								</div>
							</div>
						</div>
						<div>
							<div class="flex items-center gap-2">
								<span class="font-semibold text-gray-900 dark:text-white">{modelName}</span>
								<span class="text-xs px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-700 dark:bg-emerald-900/50 dark:text-emerald-300 animate-pulse">
									{status}
								</span>
							</div>
							<div class="text-xs text-gray-500 dark:text-gray-400">{$i18n.t('is speaking...')}</div>
						</div>
					{:else if paused}
						<div class="w-10 h-10 rounded-full bg-amber-100 dark:bg-amber-900/30 flex items-center justify-center">
							<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="w-5 h-5 text-amber-600 dark:text-amber-400">
								<path d="M5.75 3a.75.75 0 00-.75.75v12.5c0 .414.336.75.75.75h1.5a.75.75 0 00.75-.75V3.75A.75.75 0 007.25 3h-1.5zM12.75 3a.75.75 0 00-.75.75v12.5c0 .414.336.75.75.75h1.5a.75.75 0 00.75-.75V3.75a.75.75 0 00-.75-.75h-1.5z" />
							</svg>
						</div>
						<div>
							<div class="font-semibold text-amber-700 dark:text-amber-300">{$i18n.t('Symposium Paused')}</div>
							<div class="text-xs text-gray-500 dark:text-gray-400">{$i18n.t('Resume from the control panel')}</div>
						</div>
					{:else}
						<div class="relative">
							<div class="w-10 h-10 rounded-full bg-gradient-to-br from-emerald-400 to-teal-500 flex items-center justify-center">
								<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="w-5 h-5 text-white">
									<path d="M10 9a3 3 0 100-6 3 3 0 000 6zM6 8a2 2 0 11-4 0 2 2 0 014 0zM1.49 15.326a.78.78 0 01-.358-.442 3 3 0 014.308-3.516 6.484 6.484 0 00-1.905 3.959c-.023.222-.014.442.025.654a4.97 4.97 0 01-2.07-.655zM16.44 15.98a4.97 4.97 0 002.07-.654.78.78 0 00.357-.442 3 3 0 00-4.308-3.517 6.484 6.484 0 011.907 3.96 2.32 2.32 0 01-.026.654zM18 8a2 2 0 11-4 0 2 2 0 014 0zM5.304 16.19a.844.844 0 01-.277-.71 5 5 0 019.947 0 .843.843 0 01-.277.71A6.975 6.975 0 0110 18a6.974 6.974 0 01-4.696-1.81z" />
								</svg>
							</div>
							<!-- Countdown Ring -->
							{#if countdown > 0}
								<svg class="absolute inset-0 w-10 h-10 -rotate-90">
									<circle
										cx="20"
										cy="20"
										r="18"
										fill="none"
										stroke="currentColor"
										stroke-width="2"
										class="text-emerald-500/30"
									/>
									<circle
										cx="20"
										cy="20"
										r="18"
										fill="none"
										stroke="currentColor"
										stroke-width="2"
										stroke-linecap="round"
										stroke-dasharray={113}
										stroke-dashoffset={113 - (113 * (interval - countdown) / interval)}
										class="text-emerald-500 transition-all duration-1000"
									/>
								</svg>
							{/if}
						</div>
						<div>
							<div class="font-semibold text-gray-900 dark:text-white">{$i18n.t('Symposium Active')}</div>
							{#if countdown > 0}
								<div class="text-xs text-gray-500 dark:text-gray-400">
									{$i18n.t('Next response in')} <span class="font-mono text-emerald-600 dark:text-emerald-400">{countdown}s</span>
								</div>
							{/if}
						</div>
					{/if}
				</div>

				<!-- Right: Participant Avatars & Expand -->
				<div class="flex items-center gap-3">
					<!-- Participant Stack -->
					<div class="flex -space-x-2">
						{#each participantModels.slice(0, 4) as participant, idx (participant.id)}
							<div class="relative" style="z-index: {4 - idx};">
								<img
									src={participant.image}
									alt={participant.name}
									class="w-8 h-8 rounded-full object-cover border-2 border-white dark:border-gray-900 {participant.id === currentModel ? 'ring-2 ring-emerald-500' : ''}"
									title={participant.name}
								/>
								{#if participant.state === 'muted'}
									<div class="absolute -bottom-0.5 -right-0.5 w-3 h-3 bg-gray-400 rounded-full border border-white dark:border-gray-900 flex items-center justify-center text-[8px]">
										🔇
									</div>
								{:else if participant.state === 'listening'}
									<div class="absolute -bottom-0.5 -right-0.5 w-3 h-3 bg-amber-400 rounded-full border border-white dark:border-gray-900 flex items-center justify-center text-[8px]">
										👂
									</div>
								{/if}
							</div>
						{/each}
						{#if participantModels.length > 4}
							<div class="w-8 h-8 rounded-full bg-gray-200 dark:bg-gray-700 border-2 border-white dark:border-gray-900 flex items-center justify-center text-xs font-medium text-gray-600 dark:text-gray-300">
								+{participantModels.length - 4}
							</div>
						{/if}
					</div>

					<!-- Expand Button -->
					<button
						class="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
						on:click={() => expanded = !expanded}
						title={expanded ? $i18n.t('Collapse') : $i18n.t('Expand')}
					>
						<svg 
							xmlns="http://www.w3.org/2000/svg" 
							viewBox="0 0 20 20" 
							fill="currentColor" 
							class="w-4 h-4 text-gray-500 transition-transform {expanded ? 'rotate-180' : ''}"
						>
							<path fill-rule="evenodd" d="M5.23 7.21a.75.75 0 011.06.02L10 11.168l3.71-3.938a.75.75 0 111.08 1.04l-4.25 4.5a.75.75 0 01-1.08 0l-4.25-4.5a.75.75 0 01.02-1.06z" clip-rule="evenodd" />
						</svg>
					</button>
				</div>
			</div>
		</div>

		<!-- Expanded Participant Details -->
		{#if expanded}
			<div class="border-t border-emerald-200/50 dark:border-emerald-800/50 px-4 py-3" transition:slide={{ duration: 200 }}>
				<div class="max-w-5xl mx-auto">
					<div class="text-xs font-medium text-gray-500 dark:text-gray-400 mb-2">{$i18n.t('Participants')}</div>
					<div class="flex flex-wrap gap-2">
						{#each participantModels as participant (participant.id)}
							<div 
								class="flex items-center gap-2 px-3 py-1.5 rounded-full bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 transition-all
									{participant.id === currentModel ? 'ring-2 ring-emerald-500 ring-offset-1' : ''}
									{participant.state === 'muted' ? 'opacity-50' : ''}"
							>
								<img
									src={participant.image}
									alt={participant.name}
									class="w-5 h-5 rounded-full object-cover"
								/>
								<span class="text-sm font-medium">{participant.name}</span>
								<span class="text-xs" title={participant.state}>{getStateIcon(participant.state)}</span>
							</div>
						{/each}
					</div>
				</div>
			</div>
		{/if}
	</div>
{/if}

<style>
	@keyframes pulse-soft {
		0%, 100% { opacity: 1; }
		50% { opacity: 0.5; }
	}
</style>
