<script lang="ts">
	import { models, socket } from '$lib/stores';
	import { getContext, onMount, onDestroy, tick } from 'svelte';
	import { WEBUI_API_BASE_URL } from '$lib/constants';
	import SymposiumControls from './SymposiumControls.svelte';
	import Tooltip from '../common/Tooltip.svelte';
	import { toast } from 'svelte-sonner';
	import { slide } from 'svelte/transition';

	const i18n = getContext('i18n');

	export let chat;

	let symposiumModels = [];
	let modelStatuses: Record<string, string | null> = {};
	let botStates: Record<string, string> = {};
	let speakingStats: Record<string, { message_count: number; word_count: number; last_spoke: number }> = {};
	let currentSpeaker: string | null = null;
	let isSymposiumActive = false;
	
	let selectedAddModel = '';
	let whisperTarget: string | null = null;
	let whisperContent = '';
	
	// UI state
	let activeTab = 'participants';
	let showRulesEditor = false;
	let rulesText = '';

	$: if (chat && chat.config && chat.config.models) {
		symposiumModels = chat.config.models.map((id: string) => {
			const m = $models.find((m) => m.id === id);
			return m ? m : { id: id, name: id };
		});
		rulesText = chat.config?.rules?.custom || '';
	}

	// Fetch initial symposium status
	const fetchSymposiumStatus = async () => {
		try {
			const res = await fetch(`${WEBUI_API_BASE_URL}/chats/${chat.id}/symposium/status`, {
				headers: { authorization: `Bearer ${localStorage.token}` }
			});
			if (res.ok) {
				const data = await res.json();
				isSymposiumActive = data.active;
				currentSpeaker = data.current_speaker;
				botStates = data.bot_states || {};
				speakingStats = data.speaking_stats || {};
			}
		} catch (e) {
			console.error('Error fetching symposium status:', e);
		}
	};

	const onSymposiumStatus = (data: any) => {
		if (data.chat_id === chat.id) {
			if (data.status) {
				modelStatuses[data.model] = data.status;
				currentSpeaker = data.model;
			} else {
				modelStatuses[data.model] = null;
				currentSpeaker = null;
			}
		}
	};

	const onBotStateChange = (data: any) => {
		if (data.chat_id === chat.id) {
			botStates[data.model_id] = data.state;
			botStates = botStates;
		}
	};

	const onSymposiumStarted = (data: any) => {
		if (data.chat_id === chat.id) {
			isSymposiumActive = true;
		}
	};

	const onSymposiumStopped = (data: any) => {
		if (data.chat_id === chat.id) {
			isSymposiumActive = false;
			currentSpeaker = null;
		}
	};

	const onSymposiumMessage = (data: any) => {
		if (data.chat_id === chat.id && data.message) {
			// Update speaking stats locally
			const modelId = data.message.model;
			const wordCount = (data.message.content || '').split(/\s+/).length;
			if (!speakingStats[modelId]) {
				speakingStats[modelId] = { message_count: 0, word_count: 0, last_spoke: 0 };
			}
			speakingStats[modelId].message_count++;
			speakingStats[modelId].word_count += wordCount;
			speakingStats[modelId].last_spoke = Date.now() / 1000;
			speakingStats = speakingStats;
		}
	};

	const updateParticipants = async (newModels: string[]) => {
		try {
			const res = await fetch(`${WEBUI_API_BASE_URL}/chats/${chat.id}/symposium/config`, {
				method: 'PUT',
				headers: {
					'Content-Type': 'application/json',
					authorization: `Bearer ${localStorage.token}`
				},
				body: JSON.stringify({ models: newModels })
			});
			if (res.ok) {
				chat.config.models = newModels;
				toast.success($i18n.t('Participants updated'));
			} else {
				toast.error($i18n.t('Failed to update participants'));
			}
		} catch (error) {
			console.error('Error updating participants:', error);
			toast.error($i18n.t('Network error updating participants'));
		}
	};

	const addParticipant = () => {
		if (selectedAddModel && !chat.config.models.includes(selectedAddModel)) {
			updateParticipants([...chat.config.models, selectedAddModel]);
			selectedAddModel = '';
		}
	};

	const removeParticipant = (id: string) => {
		// Ensure at least 2 participants remain after removal
		const currentCount = chat.config.models.length;
		if (currentCount <= 2) {
			toast.error($i18n.t('Symposium requires at least 2 participants'));
			return;
		}
		updateParticipants(chat.config.models.filter((m: string) => m !== id));
	};

	const triggerModel = async (modelId: string) => {
		try {
			const res = await fetch(`${WEBUI_API_BASE_URL}/chats/${chat.id}/symposium/trigger`, {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					authorization: `Bearer ${localStorage.token}`
				},
				body: JSON.stringify({ model_id: modelId })
			});
			if (res.ok) {
				toast.success($i18n.t('Model triggered to speak next'));
			} else {
				toast.error($i18n.t('Failed to trigger model'));
			}
		} catch (error) {
			console.error('Error triggering model:', error);
			toast.error($i18n.t('Network error'));
		}
	};

	const setBotState = async (modelId: string, state: string) => {
		try {
			const res = await fetch(`${WEBUI_API_BASE_URL}/chats/${chat.id}/symposium/bot-state`, {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					authorization: `Bearer ${localStorage.token}`
				},
				body: JSON.stringify({ model_id: modelId, state })
			});
			if (res.ok) {
				botStates[modelId] = state;
				botStates = botStates;
				toast.success($i18n.t('Bot state updated'));
			}
		} catch (error) {
			console.error('Error setting bot state:', error);
		}
	};

	const sendWhisper = async () => {
		if (!whisperTarget || !whisperContent.trim()) return;
		const res = await fetch(`${WEBUI_API_BASE_URL}/chats/${chat.id}/symposium/whisper`, {
			method: 'POST',
			headers: {
				'Content-Type': 'application/json',
				authorization: `Bearer ${localStorage.token}`
			},
			body: JSON.stringify({ model_id: whisperTarget, content: whisperContent })
		});
		if (res.ok) {
			toast.success($i18n.t('Private instruction sent'));
			whisperTarget = null;
			whisperContent = '';
		}
	};

	const saveRules = async () => {
		try {
			const res = await fetch(`${WEBUI_API_BASE_URL}/chats/${chat.id}/symposium/config`, {
				method: 'PUT',
				headers: {
					'Content-Type': 'application/json',
					authorization: `Bearer ${localStorage.token}`
				},
				body: JSON.stringify({ 
					rules: { custom: rulesText }
				})
			});
			if (res.ok) {
				toast.success($i18n.t('Rules saved'));
				showRulesEditor = false;
			}
		} catch (e) {
			toast.error($i18n.t('Failed to save rules'));
		}
	};

	const getBotStateIcon = (state: string) => {
		switch (state) {
			case 'speaking': return '🎤';
			case 'listening': return '👂';
			case 'muted': return '🔇';
			case 'active': 
			default: return '💬';
		}
	};

	const getBotStateColor = (state: string) => {
		switch (state) {
			case 'speaking': return 'text-emerald-500';
			case 'listening': return 'text-amber-500';
			case 'muted': return 'text-gray-400';
			case 'active': 
			default: return 'text-blue-500';
		}
	};

	const formatLastSpoke = (timestamp: number) => {
		if (!timestamp) return $i18n.t('Never');
		const seconds = Math.floor(Date.now() / 1000 - timestamp);
		if (seconds < 60) return $i18n.t('Just now');
		if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
		return `${Math.floor(seconds / 3600)}h ago`;
	};

	onMount(() => {
		$socket?.on('symposium:status', onSymposiumStatus);
		$socket?.on('symposium:bot_state', onBotStateChange);
		$socket?.on('symposium:started', onSymposiumStarted);
		$socket?.on('symposium:stopped', onSymposiumStopped);
		$socket?.on('symposium:message', onSymposiumMessage);
		fetchSymposiumStatus();
	});

	onDestroy(() => {
		$socket?.off('symposium:status', onSymposiumStatus);
		$socket?.off('symposium:bot_state', onBotStateChange);
		$socket?.off('symposium:started', onSymposiumStarted);
		$socket?.off('symposium:stopped', onSymposiumStopped);
		$socket?.off('symposium:message', onSymposiumMessage);
	});
</script>

<div class="h-full w-full bg-gray-50 dark:bg-gray-900 border-l border-gray-200 dark:border-gray-800 flex flex-col">
	<!-- Header -->
	<div class="p-4 border-b border-gray-200 dark:border-gray-800">
		<div class="flex items-center justify-between mb-2">
			<div class="flex items-center gap-2">
				<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="w-5 h-5 text-emerald-500">
					<path d="M10 9a3 3 0 100-6 3 3 0 000 6zM6 8a2 2 0 11-4 0 2 2 0 014 0zM1.49 15.326a.78.78 0 01-.358-.442 3 3 0 014.308-3.516 6.484 6.484 0 00-1.905 3.959c-.023.222-.014.442.025.654a4.97 4.97 0 01-2.07-.655zM16.44 15.98a4.97 4.97 0 002.07-.654.78.78 0 00.357-.442 3 3 0 00-4.308-3.517 6.484 6.484 0 011.907 3.96 2.32 2.32 0 01-.026.654zM18 8a2 2 0 11-4 0 2 2 0 014 0zM5.304 16.19a.844.844 0 01-.277-.71 5 5 0 019.947 0 .843.843 0 01-.277.71A6.975 6.975 0 0110 18a6.974 6.974 0 01-4.696-1.81z" />
				</svg>
				<span class="font-semibold">{$i18n.t('Symposium')}</span>
			</div>
			<div class="flex items-center gap-1.5">
				{#if isSymposiumActive}
					<span class="flex items-center gap-1 text-xs px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-700 dark:bg-emerald-900/50 dark:text-emerald-300">
						<span class="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></span>
						{$i18n.t('Active')}
					</span>
				{:else}
					<span class="text-xs px-2 py-0.5 rounded-full bg-gray-200 text-gray-600 dark:bg-gray-700 dark:text-gray-400">
						{$i18n.t('Paused')}
					</span>
				{/if}
			</div>
		</div>
		
		<!-- Tab Navigation -->
		<div class="flex gap-1 p-0.5 bg-gray-200 dark:bg-gray-800 rounded-lg">
			<button
				class="flex-1 text-xs py-1.5 px-2 rounded-md transition-colors {activeTab === 'participants' ? 'bg-white dark:bg-gray-700 shadow-sm font-medium' : 'hover:bg-gray-100 dark:hover:bg-gray-700/50'}"
				on:click={() => activeTab = 'participants'}
			>
				{$i18n.t('Bots')}
			</button>
			<button
				class="flex-1 text-xs py-1.5 px-2 rounded-md transition-colors {activeTab === 'stats' ? 'bg-white dark:bg-gray-700 shadow-sm font-medium' : 'hover:bg-gray-100 dark:hover:bg-gray-700/50'}"
				on:click={() => activeTab = 'stats'}
			>
				{$i18n.t('Stats')}
			</button>
			<button
				class="flex-1 text-xs py-1.5 px-2 rounded-md transition-colors {activeTab === 'settings' ? 'bg-white dark:bg-gray-700 shadow-sm font-medium' : 'hover:bg-gray-100 dark:hover:bg-gray-700/50'}"
				on:click={() => activeTab = 'settings'}
			>
				{$i18n.t('Settings')}
			</button>
		</div>
	</div>

	<!-- Tab Content -->
	<div class="flex-1 overflow-y-auto">
		{#if activeTab === 'participants'}
			<!-- Add Participant -->
			<div class="p-3 border-b border-gray-200 dark:border-gray-800">
				<div class="flex gap-2">
					<select
						class="flex-1 text-xs rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 dark:text-white px-2 py-1.5"
						bind:value={selectedAddModel}
					>
						<option value="">{$i18n.t('Add participant...')}</option>
						{#each $models.filter((m) => !chat.config.models.includes(m.id)) as model}
							<option value={model.id}>{model.name}</option>
						{/each}
					</select>
					<button
						class="px-3 py-1.5 bg-emerald-500 hover:bg-emerald-600 text-white text-xs rounded-lg disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
						on:click={addParticipant}
						disabled={!selectedAddModel}
					>
						{$i18n.t('Add')}
					</button>
				</div>
			</div>

			<!-- Participants List -->
			<div class="p-3 space-y-2">
				{#each symposiumModels as model (model.id)}
					<div 
						class="bg-white dark:bg-gray-800 rounded-xl p-3 border border-gray-200 dark:border-gray-700 transition-all {currentSpeaker === model.id ? 'ring-2 ring-emerald-500 ring-opacity-50' : ''}"
						transition:slide={{ duration: 200 }}
					>
						<div class="flex items-center gap-3">
							<!-- Avatar with status -->
							<div class="relative">
								<img
									src={model.info?.meta?.profile_image_url ??
										(model.id
											? `${WEBUI_API_BASE_URL}/models/model/profile/image?id=${encodeURIComponent(model.id)}&lang=${$i18n.language}`
											: '/favicon.png')}
									alt={model.name}
									class="w-10 h-10 rounded-full object-cover border-2 {currentSpeaker === model.id ? 'border-emerald-500' : 'border-transparent'}"
								/>
								{#if modelStatuses[model.id]}
									<div class="absolute -bottom-0.5 -right-0.5 w-4 h-4 bg-emerald-500 rounded-full border-2 border-white dark:border-gray-800 flex items-center justify-center">
										<div class="w-1.5 h-1.5 bg-white rounded-full animate-pulse"></div>
									</div>
								{/if}
							</div>

							<!-- Name & Status -->
							<div class="flex-1 min-w-0">
								<div class="font-medium text-sm truncate">{model.name}</div>
								<div class="flex items-center gap-1.5 text-xs {getBotStateColor(botStates[model.id] || 'active')}">
									<span>{getBotStateIcon(botStates[model.id] || 'active')}</span>
									<span class="capitalize">{botStates[model.id] || 'active'}</span>
									{#if modelStatuses[model.id]}
										<span class="text-emerald-500 animate-pulse">• {modelStatuses[model.id]}</span>
									{/if}
								</div>
							</div>
						</div>

						<!-- Bot Controls -->
						<div class="mt-3 pt-3 border-t border-gray-100 dark:border-gray-700 flex flex-wrap gap-1.5">
							<!-- State Controls -->
							<Tooltip content={$i18n.t('Active - participates in conversation')}>
								<button
									class="p-1.5 rounded-lg text-xs transition-colors {(botStates[model.id] || 'active') === 'active' ? 'bg-blue-100 text-blue-700 dark:bg-blue-900/50 dark:text-blue-300' : 'bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600'}"
									on:click={() => setBotState(model.id, 'active')}
								>
									💬
								</button>
							</Tooltip>
							<Tooltip content={$i18n.t('Listening - responds only when tagged')}>
								<button
									class="p-1.5 rounded-lg text-xs transition-colors {botStates[model.id] === 'listening' ? 'bg-amber-100 text-amber-700 dark:bg-amber-900/50 dark:text-amber-300' : 'bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600'}"
									on:click={() => setBotState(model.id, 'listening')}
								>
									👂
								</button>
							</Tooltip>
							<Tooltip content={$i18n.t('Muted - silent observer')}>
								<button
									class="p-1.5 rounded-lg text-xs transition-colors {botStates[model.id] === 'muted' ? 'bg-gray-300 text-gray-700 dark:bg-gray-600 dark:text-gray-300' : 'bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600'}"
									on:click={() => setBotState(model.id, 'muted')}
								>
									🔇
								</button>
							</Tooltip>

							<div class="w-px h-5 bg-gray-200 dark:bg-gray-700 mx-1"></div>

							<!-- Action Controls -->
							<Tooltip content={$i18n.t('Force speak next')}>
								<button
									class="p-1.5 rounded-lg bg-gray-100 dark:bg-gray-700 hover:bg-emerald-100 dark:hover:bg-emerald-900/50 text-xs transition-colors"
									on:click={() => triggerModel(model.id)}
								>
									▶️
								</button>
							</Tooltip>
							<Tooltip content={$i18n.t('Send private instruction')}>
								<button
									class="p-1.5 rounded-lg text-xs transition-colors {whisperTarget === model.id ? 'bg-purple-100 text-purple-700 dark:bg-purple-900/50 dark:text-purple-300' : 'bg-gray-100 dark:bg-gray-700 hover:bg-purple-100 dark:hover:bg-purple-900/50'}"
									on:click={() => whisperTarget = whisperTarget === model.id ? null : model.id}
								>
									🔮
								</button>
							</Tooltip>
							<Tooltip content={$i18n.t('Remove from symposium')}>
								<button
									class="p-1.5 rounded-lg bg-gray-100 dark:bg-gray-700 hover:bg-red-100 dark:hover:bg-red-900/50 text-xs transition-colors"
									on:click={() => removeParticipant(model.id)}
								>
									❌
								</button>
							</Tooltip>
						</div>

						<!-- Whisper Input -->
						{#if whisperTarget === model.id}
							<div class="mt-3 p-2 bg-purple-50 dark:bg-purple-900/20 rounded-lg border border-purple-200 dark:border-purple-800" transition:slide={{ duration: 150 }}>
								<div class="text-xs text-purple-700 dark:text-purple-300 mb-1.5 font-medium">
									🔮 {$i18n.t('Whisper to')} {model.name}
								</div>
								<textarea
									class="w-full h-16 text-xs p-2 rounded-lg border border-purple-200 dark:border-purple-700 bg-white dark:bg-gray-900 resize-none outline-none focus:ring-2 focus:ring-purple-500"
									placeholder={$i18n.t('Enter private instruction that only this bot will see...')}
									bind:value={whisperContent}
								></textarea>
								<div class="flex justify-end gap-2 mt-2">
									<button
										class="px-3 py-1 text-xs rounded-lg bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600"
										on:click={() => { whisperTarget = null; whisperContent = ''; }}
									>
										{$i18n.t('Cancel')}
									</button>
									<button
										class="px-3 py-1 bg-purple-500 text-white text-xs rounded-lg hover:bg-purple-600 disabled:opacity-50"
										on:click={sendWhisper}
										disabled={!whisperContent.trim()}
									>
										{$i18n.t('Send Whisper')}
									</button>
								</div>
							</div>
						{/if}
					</div>
				{/each}
			</div>

		{:else if activeTab === 'stats'}
			<!-- Speaking Statistics -->
			<div class="p-4 space-y-4">
				<div class="text-xs text-gray-500 dark:text-gray-400 uppercase tracking-wider font-medium mb-2">
					{$i18n.t('Speaking Statistics')}
				</div>
				
				{#each symposiumModels as model (model.id)}
					{@const stats = speakingStats[model.id] || { message_count: 0, word_count: 0, last_spoke: 0 }}
					<div class="bg-white dark:bg-gray-800 rounded-xl p-3 border border-gray-200 dark:border-gray-700">
						<div class="flex items-center gap-2 mb-2">
							<img
								src={model.info?.meta?.profile_image_url ??
									(model.id
										? `${WEBUI_API_BASE_URL}/models/model/profile/image?id=${encodeURIComponent(model.id)}&lang=${$i18n.language}`
										: '/favicon.png')}
								alt={model.name}
								class="w-6 h-6 rounded-full object-cover"
							/>
							<span class="font-medium text-sm truncate">{model.name}</span>
						</div>
						<div class="grid grid-cols-3 gap-2 text-center">
							<div class="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-2">
								<div class="text-lg font-bold text-emerald-600 dark:text-emerald-400">{stats.message_count}</div>
								<div class="text-xs text-gray-500">{$i18n.t('Messages')}</div>
							</div>
							<div class="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-2">
								<div class="text-lg font-bold text-blue-600 dark:text-blue-400">{stats.word_count}</div>
								<div class="text-xs text-gray-500">{$i18n.t('Words')}</div>
							</div>
							<div class="bg-gray-50 dark:bg-gray-700/50 rounded-lg p-2">
								<div class="text-xs font-medium text-purple-600 dark:text-purple-400">{formatLastSpoke(stats.last_spoke)}</div>
								<div class="text-xs text-gray-500">{$i18n.t('Last spoke')}</div>
							</div>
						</div>
					</div>
				{/each}

				{#if Object.keys(speakingStats).length === 0}
					<div class="text-center text-gray-500 dark:text-gray-400 py-8">
						<div class="text-3xl mb-2">📊</div>
						<div class="text-sm">{$i18n.t('No speaking activity yet')}</div>
					</div>
				{/if}
			</div>

		{:else if activeTab === 'settings'}
			<!-- Symposium Settings -->
			<div class="p-4 space-y-4">
				<!-- Rules Section -->
				<div class="bg-white dark:bg-gray-800 rounded-xl p-4 border border-gray-200 dark:border-gray-700">
					<div class="flex items-center justify-between mb-3">
						<div class="font-medium text-sm">{$i18n.t('Symposium Rules')}</div>
						<button
							class="text-xs text-blue-500 hover:text-blue-600"
							on:click={() => showRulesEditor = !showRulesEditor}
						>
							{showRulesEditor ? $i18n.t('Cancel') : $i18n.t('Edit')}
						</button>
					</div>
					
					{#if showRulesEditor}
						<div transition:slide={{ duration: 150 }}>
							<textarea
								class="w-full h-32 text-xs p-2 rounded-lg border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900 resize-none outline-none focus:ring-2 focus:ring-blue-500"
								placeholder={$i18n.t('Enter custom rules for the symposium...\n\nExample:\n- Stay on topic\n- Be respectful\n- Maximum 200 words per response')}
								bind:value={rulesText}
							></textarea>
							<div class="flex justify-end mt-2">
								<button
									class="px-3 py-1.5 bg-blue-500 text-white text-xs rounded-lg hover:bg-blue-600"
									on:click={saveRules}
								>
									{$i18n.t('Save Rules')}
								</button>
							</div>
						</div>
					{:else}
						<div class="text-xs text-gray-600 dark:text-gray-400 bg-gray-50 dark:bg-gray-900 p-2 rounded-lg">
							{rulesText || $i18n.t('No custom rules defined. Click Edit to add rules.')}
						</div>
					{/if}
				</div>

				<!-- Quick Tips -->
				<div class="bg-gradient-to-br from-emerald-50 to-blue-50 dark:from-emerald-900/20 dark:to-blue-900/20 rounded-xl p-4 border border-emerald-200 dark:border-emerald-800">
					<div class="font-medium text-sm mb-2 text-emerald-700 dark:text-emerald-300">💡 {$i18n.t('Tips')}</div>
					<ul class="text-xs text-gray-600 dark:text-gray-400 space-y-1.5">
						<li>• {$i18n.t('Use @ to tag a specific bot in your messages')}</li>
						<li>• {$i18n.t('Set bots to "listening" mode to have them observe')}</li>
						<li>• {$i18n.t('Whispers are private instructions only one bot sees')}</li>
						<li>• {$i18n.t('Force speak to make a specific bot respond next')}</li>
					</ul>
				</div>
			</div>
		{/if}
	</div>

	<!-- Controls Footer -->
	<div class="border-t border-gray-200 dark:border-gray-800">
		<SymposiumControls {chat} />
	</div>
</div>
