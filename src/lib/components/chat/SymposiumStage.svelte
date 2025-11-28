<script lang="ts">
	import { onMount, getContext, onDestroy } from 'svelte';
	import { fade, scale } from 'svelte/transition';
	import { WEBUI_API_BASE_URL } from '$lib/constants';
	import { models, socket } from '$lib/stores';

	export let chat;

	const i18n = getContext('i18n');

	let participants = [];
	let currentSpeaker = null;
	let botStates = {};

	// Map of bot id -> animation state
	let animations = {};

	$: if (chat && chat.config && chat.config.models) {
		participants = chat.config.models.map((id) => {
			const m = $models.find((m) => m.id === id);
			return m ? m : { id: id, name: id };
		});
	}

	const fetchStatus = async () => {
		try {
			const res = await fetch(`${WEBUI_API_BASE_URL}/chats/${chat.id}/symposium/status`, {
				headers: { authorization: `Bearer ${localStorage.token}` }
			});
			if (res.ok) {
				const data = await res.json();
				currentSpeaker = data.current_speaker;
				botStates = data.bot_states || {};
			}
		} catch (e) {
			console.error(e);
		}
	};

	const onSymposiumStatus = (data) => {
		if (data.chat_id === chat.id) {
			if (data.status) {
				currentSpeaker = data.model;
			} else {
				currentSpeaker = null;
			}
		}
	};

	const onBotStateChange = (data) => {
		if (data.chat_id === chat.id) {
			botStates[data.model_id] = data.state;
			botStates = botStates; // Trigger update
		}
	};

	onMount(() => {
		fetchStatus();
		$socket?.on('symposium:status', onSymposiumStatus);
		$socket?.on('symposium:bot_state', onBotStateChange);
	});

	onDestroy(() => {
		$socket?.off('symposium:status', onSymposiumStatus);
		$socket?.off('symposium:bot_state', onBotStateChange);
	});

	// Helper to calculate position in circle
	const getPosition = (index, total) => {
		if (total === 0) return { x: 0, y: 0 };
		const angle = (index / total) * 2 * Math.PI - Math.PI / 2; // Start at top
		const radius = 120; // Radius in pixels
		return {
			x: Math.cos(angle) * radius,
			y: Math.sin(angle) * radius
		};
	};

</script>

<div class="w-full h-80 relative flex items-center justify-center bg-gradient-to-br from-gray-50 to-gray-100 dark:from-gray-900 dark:to-gray-950 rounded-xl border border-gray-200 dark:border-gray-800 overflow-hidden mb-4 shadow-inner">

	<!-- Center Table/Logo -->
	<div class="absolute w-32 h-32 rounded-full bg-white/50 dark:bg-gray-800/50 backdrop-blur-sm border border-white/20 flex items-center justify-center shadow-lg z-0">
		<div class="text-4xl opacity-20">💬</div>
	</div>

	<!-- Participants -->
	<div class="relative w-64 h-64 z-10">
		{#each participants as participant, i (participant.id)}
			{@const pos = getPosition(i, participants.length)}
			{@const isSpeaking = currentSpeaker === participant.id}
			{@const state = botStates[participant.id] || 'active'}

			<div
				class="absolute w-16 h-16 -ml-8 -mt-8 transition-all duration-500 ease-out"
				style="left: {50 + (pos.x / 2.5)}%; top: {50 + (pos.y / 2.5)}%;"
			>
				<!-- Avatar Container -->
				<div
					class="relative w-full h-full rounded-full transition-transform duration-300
					{isSpeaking ? 'scale-125 z-20' : 'scale-100 z-10'}
					{state === 'muted' ? 'opacity-50 grayscale' : 'opacity-100'}"
				>
					<!-- Pulse Effect when Speaking -->
					{#if isSpeaking}
						<div class="absolute inset-0 rounded-full bg-emerald-500/30 animate-ping"></div>
						<div class="absolute -inset-1 rounded-full bg-gradient-to-r from-emerald-500 to-teal-500 opacity-75 blur-sm"></div>
					{/if}

					<!-- Profile Image -->
					<img
						src={participant.info?.meta?.profile_image_url ?? `${WEBUI_API_BASE_URL}/models/model/profile/image?id=${encodeURIComponent(participant.id)}`}
						alt={participant.name}
						class="w-full h-full rounded-full object-cover border-2 shadow-lg bg-white dark:bg-gray-800
							{isSpeaking ? 'border-emerald-500' : 'border-white dark:border-gray-700'}"
					/>

					<!-- Status Badge -->
					<div class="absolute -bottom-1 -right-1 w-6 h-6 rounded-full bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 flex items-center justify-center shadow-sm text-xs z-30">
						{#if isSpeaking}
							<span class="animate-pulse">🎙️</span>
						{:else if state === 'listening'}
							<span>👂</span>
						{:else if state === 'muted'}
							<span>🔇</span>
						{:else}
							<div class="w-2 h-2 rounded-full bg-green-500"></div>
						{/if}
					</div>

					<!-- Name Tooltip (Always visible if speaking, else on hover) -->
					<div class="absolute -bottom-8 left-1/2 -translate-x-1/2 whitespace-nowrap px-2 py-0.5 rounded-md bg-black/75 text-white text-[10px] font-medium transition-opacity
						{isSpeaking ? 'opacity-100' : 'opacity-0 group-hover:opacity-100'}">
						{participant.name}
					</div>
				</div>
			</div>
		{/each}
	</div>

	<div class="absolute bottom-2 right-3 text-xs text-gray-400 font-medium tracking-wide uppercase">
		{$i18n.t('Stage View')}
	</div>
</div>
