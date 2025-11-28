<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { createEventDispatcher, getContext, onMount } from 'svelte';
	import { models } from '$lib/stores';
	import Modal from '../common/Modal.svelte';
	import { createNewChat } from '$lib/apis/chats';
	import { goto } from '$app/navigation';
	import { WEBUI_API_BASE_URL } from '$lib/constants';
	import { slide, fade } from 'svelte/transition';
	import Tooltip from '../common/Tooltip.svelte';

	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	export let show = false;

	// Form state
	let title = '';
	let selectedModels: string[] = [];
	let prompt = '';
	let interval = 30;
	let contextLimit = 20;
	let step = 1; // Wizard step: 1=topic, 2=participants, 3=configure
	
	// Search and filter
	let modelSearch = '';
	let selectedCategory = 'all';

	// Presets organized by category
	const presetCategories = [
		{
			id: 'debate',
			name: 'Debates',
			icon: '⚔️',
			color: 'from-red-500 to-orange-500',
			presets: [
				{
					name: 'Philosophical Showdown',
					description: 'A clash of worldviews: materialism vs idealism',
					prompt: 'You are participating in a philosophical debate about the nature of consciousness. Engage thoughtfully, present arguments, and respond to counterpoints. Be respectful but rigorous in your reasoning.',
					interval: 45,
					models: 2,
					icon: '🧠'
				},
				{
					name: 'Tech Ethics Forum',
					description: 'AI, privacy, and the future of humanity',
					prompt: 'Debate the ethical implications of AI development. Consider privacy, autonomy, job displacement, and existential risk. Present balanced arguments while defending your assigned position.',
					interval: 40,
					models: 3,
					icon: '⚖️'
				},
				{
					name: 'Political Roundtable',
					description: 'Different perspectives on governance',
					prompt: 'Engage in a thoughtful political discussion. Present different ideological perspectives while maintaining civility. Focus on policy implications rather than personal attacks.',
					interval: 50,
					models: 4,
					icon: '🏛️'
				}
			]
		},
		{
			id: 'creative',
			name: 'Creative',
			icon: '🎨',
			color: 'from-purple-500 to-pink-500',
			presets: [
				{
					name: 'Story Workshop',
					description: 'Collaborative fiction writing',
					prompt: 'You are co-writing a story together. Build on each other\'s contributions, maintain narrative consistency, and create compelling characters. Take turns advancing the plot.',
					interval: 60,
					models: 2,
					icon: '📖'
				},
				{
					name: 'World Building',
					description: 'Create entire universes together',
					prompt: 'Collaboratively build a detailed fictional world. Discuss geography, cultures, magic systems, history, and inhabitants. Build on each other\'s ideas to create a cohesive universe.',
					interval: 45,
					models: 3,
					icon: '🌍'
				},
				{
					name: 'Poetry Jam',
					description: 'Collaborative verse and rhythm',
					prompt: 'Create poetry together. Build on themes, respond with connected verses, and explore different styles. Let the creative flow guide you.',
					interval: 30,
					models: 2,
					icon: '✨'
				}
			]
		},
		{
			id: 'learning',
			name: 'Learning',
			icon: '📚',
			color: 'from-blue-500 to-cyan-500',
			presets: [
				{
					name: 'Socratic Seminar',
					description: 'Deep questioning and exploration',
					prompt: 'Engage in Socratic dialogue to explore complex topics. Ask probing questions, challenge assumptions, and seek deeper understanding through conversation.',
					interval: 40,
					models: 2,
					icon: '🤔'
				},
				{
					name: 'Tutor Session',
					description: 'Teaching and learning together',
					prompt: 'One participant teaches while others learn and ask questions. Provide clear explanations, use examples, and ensure understanding before moving on.',
					interval: 45,
					models: 2,
					icon: '👨‍🏫'
				},
				{
					name: 'Research Collaboration',
					description: 'Explore topics in depth',
					prompt: 'Work together to research and understand a complex topic. Share knowledge, analyze sources, and build a comprehensive understanding.',
					interval: 60,
					models: 3,
					icon: '🔬'
				}
			]
		},
		{
			id: 'roleplay',
			name: 'Roleplay',
			icon: '🎭',
			color: 'from-emerald-500 to-teal-500',
			presets: [
				{
					name: 'Backrooms',
					description: 'Lost in infinite liminal spaces',
					prompt: 'You are wandering through the Backrooms - an infinite maze of yellow walls, buzzing fluorescent lights, and the smell of wet carpet. Describe your experiences, encounters, and attempts to escape.',
					interval: 30,
					models: 2,
					icon: '🚪'
				},
				{
					name: 'Space Station',
					description: 'Life aboard a distant outpost',
					prompt: 'You are crew members on a space station at the edge of explored space. Navigate daily challenges, discoveries, and the isolation of deep space together.',
					interval: 45,
					models: 3,
					icon: '🚀'
				},
				{
					name: 'Mystery Dinner',
					description: 'Solve a murder mystery',
					prompt: 'You are guests at a dinner party where a murder has occurred. Each of you has secrets. Investigate, interrogate, and try to uncover the truth.',
					interval: 40,
					models: 4,
					icon: '🔍'
				}
			]
		},
		{
			id: 'professional',
			name: 'Professional',
			icon: '💼',
			color: 'from-amber-500 to-yellow-500',
			presets: [
				{
					name: 'Brainstorm Session',
					description: 'Generate and refine ideas',
					prompt: 'Engage in a creative brainstorming session. Generate ideas freely, build on each other\'s suggestions, and work towards innovative solutions. No idea is too wild initially.',
					interval: 30,
					models: 3,
					icon: '💡'
				},
				{
					name: 'Code Review',
					description: 'Technical discussion and review',
					prompt: 'Review code and discuss technical approaches. Share insights, suggest improvements, and explain reasoning. Be constructive and thorough.',
					interval: 45,
					models: 2,
					icon: '👨‍💻'
				},
				{
					name: 'Strategy Meeting',
					description: 'Plan and analyze approaches',
					prompt: 'Discuss strategy and planning. Analyze options, consider trade-offs, and develop actionable plans. Be analytical and consider multiple perspectives.',
					interval: 50,
					models: 3,
					icon: '📊'
				}
			]
		}
	];

	let selectedPreset: any = null;
	let customMode = false;

	// Filtered models based on search
	$: filteredModels = $models.filter(m => 
		m.name.toLowerCase().includes(modelSearch.toLowerCase()) ||
		m.id.toLowerCase().includes(modelSearch.toLowerCase())
	);

	// Get model info by id
	const getModelInfo = (id: string) => $models.find(m => m.id === id);

	// Select a preset
	const selectPreset = (preset: any) => {
		selectedPreset = preset;
		prompt = preset.prompt;
		interval = preset.interval;
		title = preset.name;
		// Pre-select appropriate number of model slots
		selectedModels = Array(preset.models).fill('');
		customMode = false;
		step = 2;
	};

	// Start custom symposium
	const startCustom = () => {
		customMode = true;
		selectedPreset = null;
		selectedModels = ['', ''];
		step = 2;
	};

	// Toggle model selection
	const toggleModel = (modelId: string) => {
		if (selectedModels.includes(modelId)) {
			selectedModels = selectedModels.filter(m => m !== modelId);
		} else {
			// Replace first empty slot or add new
			const emptyIdx = selectedModels.findIndex(m => m === '');
			if (emptyIdx !== -1) {
				selectedModels[emptyIdx] = modelId;
				selectedModels = selectedModels;
			} else {
				selectedModels = [...selectedModels, modelId];
			}
		}
	};

	// Submit handler
	const submitHandler = async () => {
		const validModels = selectedModels.filter(m => m);
		
		if (validModels.length < 2) {
			toast.error($i18n.t('Please select at least 2 participants for a meaningful discussion.'));
			return;
		}

		if (!prompt.trim()) {
			toast.error($i18n.t('Please provide a topic or context for the symposium.'));
			return;
		}

		const chatConfig = {
			models: validModels,
			prompt: prompt,
			autonomous_interval: interval,
			context_limit: contextLimit,
			paused: false
		};

		const chat = await createNewChat(
			localStorage.token,
			{
				title: title || 'New Symposium',
				mode: 'symposium',
				config: chatConfig,
				models: validModels,
				history: { messages: {}, currentId: null }
			},
			null
		).catch((error) => {
			toast.error(error.detail || 'Failed to create symposium');
			return null;
		});

		if (chat) {
			show = false;
			// Reset form
			title = '';
			selectedModels = [];
			prompt = '';
			interval = 30;
			step = 1;
			selectedPreset = null;
			customMode = false;
			
			toast.success($i18n.t('Symposium started! The conversation will begin shortly.'));
			await goto(`/c/${chat.id}`);
		}
	};

	// Reset when modal closes
	$: if (!show) {
		step = 1;
		selectedPreset = null;
		customMode = false;
		modelSearch = '';
	}
</script>

<Modal bind:show size="lg">
	<div class="relative">
		<!-- Header with gradient -->
		<div class="bg-gradient-to-r from-emerald-600 via-teal-600 to-cyan-600 px-6 py-5 rounded-t-xl">
			<div class="flex justify-between items-center">
				<div class="flex items-center gap-3">
					<div class="w-10 h-10 bg-white/20 backdrop-blur-sm rounded-xl flex items-center justify-center">
						<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" class="w-6 h-6 text-white">
							<path d="M4.5 6.375a4.125 4.125 0 118.25 0 4.125 4.125 0 01-8.25 0zM14.25 8.625a3.375 3.375 0 116.75 0 3.375 3.375 0 01-6.75 0zM1.5 19.125a7.125 7.125 0 0114.25 0v.003l-.001.119a.75.75 0 01-.363.63 13.067 13.067 0 01-6.761 1.873c-2.472 0-4.786-.684-6.76-1.873a.75.75 0 01-.364-.63l-.001-.122zM17.25 19.128l-.001.144a2.25 2.25 0 01-.233.96 10.088 10.088 0 005.06-1.01.75.75 0 00.42-.643 4.875 4.875 0 00-6.957-4.611 8.586 8.586 0 011.71 5.157v.003z" />
						</svg>
					</div>
					<div>
						<h2 class="text-xl font-bold text-white">{$i18n.t('Create Symposium')}</h2>
						<p class="text-emerald-100 text-sm">{$i18n.t('Where AI minds meet to discuss')}</p>
					</div>
				</div>
				<button
					class="text-white/70 hover:text-white transition-colors p-1 hover:bg-white/10 rounded-lg"
					on:click={() => show = false}
				>
					<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="w-5 h-5">
						<path d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z" />
					</svg>
				</button>
			</div>

			<!-- Progress Steps -->
			<div class="flex items-center justify-center mt-4 gap-2">
				{#each [1, 2, 3] as s}
					<button
						class="flex items-center gap-2 transition-all {step >= s ? 'opacity-100' : 'opacity-50'}"
						on:click={() => { if (s < step || (s === 2 && selectedPreset) || (s === 2 && customMode)) step = s; }}
						disabled={s > step && !((s === 2 && selectedPreset) || (s === 2 && customMode))}
					>
						<div class="w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium transition-all
							{step === s ? 'bg-white text-emerald-600 ring-4 ring-white/30' : step > s ? 'bg-white/30 text-white' : 'bg-white/10 text-white/50'}">
							{#if step > s}
								<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="w-4 h-4">
									<path fill-rule="evenodd" d="M16.704 4.153a.75.75 0 01.143 1.052l-8 10.5a.75.75 0 01-1.127.075l-4.5-4.5a.75.75 0 011.06-1.06l3.894 3.893 7.48-9.817a.75.75 0 011.05-.143z" clip-rule="evenodd" />
								</svg>
							{:else}
								{s}
							{/if}
						</div>
						<span class="text-sm text-white/80 hidden sm:block">
							{s === 1 ? $i18n.t('Topic') : s === 2 ? $i18n.t('Participants') : $i18n.t('Configure')}
						</span>
					</button>
					{#if s < 3}
						<div class="w-12 h-0.5 {step > s ? 'bg-white/50' : 'bg-white/20'}"></div>
					{/if}
				{/each}
			</div>
		</div>

		<!-- Content -->
		<div class="p-6 bg-white dark:bg-gray-900 max-h-[60vh] overflow-y-auto">
			{#if step === 1}
				<!-- Step 1: Choose Topic/Preset -->
				<div transition:fade={{ duration: 150 }}>
					<!-- Custom Option -->
					<button
						class="w-full mb-6 p-4 rounded-xl border-2 border-dashed border-gray-300 dark:border-gray-700 hover:border-emerald-500 dark:hover:border-emerald-500 transition-all group"
						on:click={startCustom}
					>
						<div class="flex items-center gap-4">
							<div class="w-12 h-12 rounded-xl bg-gradient-to-br from-gray-100 to-gray-200 dark:from-gray-800 dark:to-gray-700 flex items-center justify-center text-2xl group-hover:scale-110 transition-transform">
								✨
							</div>
							<div class="text-left flex-1">
								<div class="font-semibold text-gray-900 dark:text-white">{$i18n.t('Custom Symposium')}</div>
								<div class="text-sm text-gray-500 dark:text-gray-400">{$i18n.t('Create your own topic and rules')}</div>
							</div>
							<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="w-5 h-5 text-gray-400 group-hover:text-emerald-500 transition-colors">
								<path fill-rule="evenodd" d="M7.21 14.77a.75.75 0 01.02-1.06L11.168 10 7.23 6.29a.75.75 0 111.04-1.08l4.5 4.25a.75.75 0 010 1.08l-4.5 4.25a.75.75 0 01-1.06-.02z" clip-rule="evenodd" />
							</svg>
						</div>
					</button>

					<div class="text-sm font-medium text-gray-500 dark:text-gray-400 mb-4">{$i18n.t('Or choose a preset')}</div>

					<!-- Preset Categories -->
					{#each presetCategories as category}
						<div class="mb-6">
							<div class="flex items-center gap-2 mb-3">
								<span class="text-lg">{category.icon}</span>
								<span class="font-medium text-gray-900 dark:text-white">{category.name}</span>
							</div>
							<div class="grid gap-3">
								{#each category.presets as preset}
									<button
										class="w-full p-4 rounded-xl border border-gray-200 dark:border-gray-700 hover:border-emerald-500 dark:hover:border-emerald-500 hover:shadow-lg transition-all text-left group bg-white dark:bg-gray-800"
										on:click={() => selectPreset(preset)}
									>
										<div class="flex items-start gap-4">
											<div class="w-10 h-10 rounded-lg bg-gradient-to-br {category.color} flex items-center justify-center text-xl flex-shrink-0 group-hover:scale-110 transition-transform">
												{preset.icon}
											</div>
											<div class="flex-1 min-w-0">
												<div class="font-medium text-gray-900 dark:text-white">{preset.name}</div>
												<div class="text-sm text-gray-500 dark:text-gray-400 line-clamp-1">{preset.description}</div>
												<div class="flex items-center gap-3 mt-2 text-xs text-gray-400">
													<span class="flex items-center gap-1">
														<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" fill="currentColor" class="w-3 h-3">
															<path d="M8 8a3 3 0 100-6 3 3 0 000 6zM12.735 14c.618 0 1.093-.561.872-1.139a6.002 6.002 0 00-11.215 0c-.22.578.254 1.139.872 1.139h9.47z" />
														</svg>
														{preset.models} bots
													</span>
													<span class="flex items-center gap-1">
														<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" fill="currentColor" class="w-3 h-3">
															<path fill-rule="evenodd" d="M1 8a7 7 0 1114 0A7 7 0 011 8zm7.75-4.25a.75.75 0 00-1.5 0V8c0 .414.336.75.75.75h3.25a.75.75 0 000-1.5h-2.5v-3.5z" clip-rule="evenodd" />
														</svg>
														{preset.interval}s
													</span>
												</div>
											</div>
											<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="w-5 h-5 text-gray-400 group-hover:text-emerald-500 transition-colors flex-shrink-0">
												<path fill-rule="evenodd" d="M7.21 14.77a.75.75 0 01.02-1.06L11.168 10 7.23 6.29a.75.75 0 111.04-1.08l4.5 4.25a.75.75 0 010 1.08l-4.5 4.25a.75.75 0 01-1.06-.02z" clip-rule="evenodd" />
											</svg>
										</div>
									</button>
								{/each}
							</div>
						</div>
					{/each}
				</div>

			{:else if step === 2}
				<!-- Step 2: Select Participants -->
				<div transition:fade={{ duration: 150 }}>
					{#if selectedPreset}
						<div class="mb-4 p-3 rounded-lg bg-emerald-50 dark:bg-emerald-900/20 border border-emerald-200 dark:border-emerald-800">
							<div class="flex items-center gap-2 text-emerald-700 dark:text-emerald-300">
								<span class="text-lg">{selectedPreset.icon}</span>
								<span class="font-medium">{selectedPreset.name}</span>
							</div>
							<p class="text-sm text-emerald-600 dark:text-emerald-400 mt-1">{selectedPreset.description}</p>
						</div>
					{/if}

					<div class="mb-4">
						<div class="flex items-center justify-between mb-2">
							<label class="text-sm font-medium text-gray-700 dark:text-gray-300">{$i18n.t('Select Participants')}</label>
							<span class="text-xs text-gray-500">{selectedModels.filter(m => m).length} {$i18n.t('selected')}</span>
						</div>
						
						<!-- Search -->
						<div class="relative mb-3">
							<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-gray-400">
								<path fill-rule="evenodd" d="M9 3.5a5.5 5.5 0 100 11 5.5 5.5 0 000-11zM2 9a7 7 0 1112.452 4.391l3.328 3.329a.75.75 0 11-1.06 1.06l-3.329-3.328A7 7 0 012 9z" clip-rule="evenodd" />
							</svg>
							<input
								type="text"
								class="w-full pl-9 pr-4 py-2 rounded-lg border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 text-sm focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 outline-none"
								placeholder={$i18n.t('Search models...')}
								bind:value={modelSearch}
							/>
						</div>

						<!-- Selected Models Preview -->
						{#if selectedModels.filter(m => m).length > 0}
							<div class="flex flex-wrap gap-2 mb-3 p-3 bg-gray-50 dark:bg-gray-800 rounded-lg">
								{#each selectedModels.filter(m => m) as modelId (modelId)}
									{@const model = getModelInfo(modelId)}
									<div class="flex items-center gap-2 bg-white dark:bg-gray-700 rounded-full pl-1 pr-2 py-1 border border-gray-200 dark:border-gray-600" transition:slide={{ duration: 150, axis: 'x' }}>
										<img
											src={model?.info?.meta?.profile_image_url ?? `${WEBUI_API_BASE_URL}/models/model/profile/image?id=${encodeURIComponent(modelId)}`}
											alt=""
											class="w-6 h-6 rounded-full object-cover"
										/>
										<span class="text-sm font-medium truncate max-w-24">{model?.name || modelId}</span>
										<button
											class="text-gray-400 hover:text-red-500 transition-colors"
											on:click={() => toggleModel(modelId)}
										>
											<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" fill="currentColor" class="w-4 h-4">
												<path d="M5.28 4.22a.75.75 0 00-1.06 1.06L6.94 8l-2.72 2.72a.75.75 0 101.06 1.06L8 9.06l2.72 2.72a.75.75 0 101.06-1.06L9.06 8l2.72-2.72a.75.75 0 00-1.06-1.06L8 6.94 5.28 4.22z" />
											</svg>
										</button>
									</div>
								{/each}
							</div>
						{/if}

						<!-- Model Grid -->
						<div class="grid grid-cols-2 sm:grid-cols-3 gap-2 max-h-64 overflow-y-auto">
							{#each filteredModels as model (model.id)}
								{@const isSelected = selectedModels.includes(model.id)}
								<button
									class="p-3 rounded-xl border-2 transition-all text-left
										{isSelected 
											? 'border-emerald-500 bg-emerald-50 dark:bg-emerald-900/20' 
											: 'border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600'}"
									on:click={() => toggleModel(model.id)}
								>
									<div class="flex items-center gap-2">
										<img
											src={model.info?.meta?.profile_image_url ?? `${WEBUI_API_BASE_URL}/models/model/profile/image?id=${encodeURIComponent(model.id)}`}
											alt=""
											class="w-8 h-8 rounded-full object-cover flex-shrink-0"
										/>
										<div class="min-w-0 flex-1">
											<div class="text-sm font-medium truncate text-gray-900 dark:text-white">{model.name}</div>
										</div>
										{#if isSelected}
											<div class="w-5 h-5 rounded-full bg-emerald-500 flex items-center justify-center flex-shrink-0">
												<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" fill="white" class="w-3 h-3">
													<path fill-rule="evenodd" d="M12.416 3.376a.75.75 0 01.208 1.04l-5 7.5a.75.75 0 01-1.154.114l-3-3a.75.75 0 011.06-1.06l2.353 2.353 4.493-6.74a.75.75 0 011.04-.207z" clip-rule="evenodd" />
												</svg>
											</div>
										{/if}
									</div>
								</button>
							{/each}
						</div>

						{#if filteredModels.length === 0}
							<div class="text-center py-8 text-gray-500">
								<p>{$i18n.t('No models found')}</p>
							</div>
						{/if}
					</div>
				</div>

			{:else if step === 3}
				<!-- Step 3: Configure -->
				<div transition:fade={{ duration: 150 }} class="space-y-5">
					<!-- Title -->
					<div>
						<label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">{$i18n.t('Symposium Title')}</label>
						<input
							type="text"
							class="w-full px-4 py-2.5 rounded-xl border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 text-sm focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 outline-none"
							placeholder={$i18n.t('Give your symposium a name...')}
							bind:value={title}
						/>
					</div>

					<!-- Topic/Context -->
					<div>
						<label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">{$i18n.t('Topic & Context')}</label>
						<textarea
							class="w-full px-4 py-3 rounded-xl border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800 text-sm focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 outline-none resize-none h-28"
							placeholder={$i18n.t('What should the participants discuss? Set the scene and context...')}
							bind:value={prompt}
						></textarea>
					</div>

					<!-- Settings Grid -->
					<div class="grid grid-cols-2 gap-4">
						<!-- Interval -->
						<div class="p-4 rounded-xl bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700">
							<div class="flex items-center gap-2 mb-2">
								<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="w-4 h-4 text-gray-500">
									<path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm.75-13a.75.75 0 00-1.5 0v5c0 .414.336.75.75.75h4a.75.75 0 000-1.5h-3.25V5z" clip-rule="evenodd" />
								</svg>
								<span class="text-sm font-medium text-gray-700 dark:text-gray-300">{$i18n.t('Response Interval')}</span>
							</div>
							<div class="text-2xl font-bold text-emerald-600 dark:text-emerald-400">{interval}s</div>
							<input
								type="range"
								min="10"
								max="120"
								step="5"
								class="w-full h-2 mt-2 bg-gray-200 rounded-lg appearance-none cursor-pointer dark:bg-gray-700 accent-emerald-500"
								bind:value={interval}
							/>
						</div>

						<!-- Context Limit -->
						<div class="p-4 rounded-xl bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700">
							<div class="flex items-center gap-2 mb-2">
								<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="w-4 h-4 text-gray-500">
									<path fill-rule="evenodd" d="M4.5 2A1.5 1.5 0 003 3.5v13A1.5 1.5 0 004.5 18h11a1.5 1.5 0 001.5-1.5V7.621a1.5 1.5 0 00-.44-1.06l-4.12-4.122A1.5 1.5 0 0011.378 2H4.5z" clip-rule="evenodd" />
								</svg>
								<span class="text-sm font-medium text-gray-700 dark:text-gray-300">{$i18n.t('Memory')}</span>
							</div>
							<div class="text-2xl font-bold text-blue-600 dark:text-blue-400">{contextLimit}</div>
							<input
								type="range"
								min="5"
								max="50"
								step="5"
								class="w-full h-2 mt-2 bg-gray-200 rounded-lg appearance-none cursor-pointer dark:bg-gray-700 accent-blue-500"
								bind:value={contextLimit}
							/>
							<div class="text-xs text-gray-500 mt-1">{$i18n.t('messages')}</div>
						</div>
					</div>

					<!-- Participants Summary -->
					<div class="p-4 rounded-xl bg-gradient-to-r from-emerald-50 to-teal-50 dark:from-emerald-900/20 dark:to-teal-900/20 border border-emerald-200 dark:border-emerald-800">
						<div class="text-sm font-medium text-emerald-800 dark:text-emerald-200 mb-2">{$i18n.t('Participants')}</div>
						<div class="flex flex-wrap gap-2">
							{#each selectedModels.filter(m => m) as modelId (modelId)}
								{@const model = getModelInfo(modelId)}
								<div class="flex items-center gap-2 bg-white dark:bg-gray-800 rounded-full px-3 py-1.5">
									<img
										src={model?.info?.meta?.profile_image_url ?? `${WEBUI_API_BASE_URL}/models/model/profile/image?id=${encodeURIComponent(modelId)}`}
										alt=""
										class="w-5 h-5 rounded-full object-cover"
									/>
									<span class="text-sm font-medium">{model?.name || modelId}</span>
								</div>
							{/each}
						</div>
					</div>
				</div>
			{/if}
		</div>

		<!-- Footer -->
		<div class="px-6 py-4 bg-gray-50 dark:bg-gray-800 border-t border-gray-200 dark:border-gray-700 rounded-b-xl">
			<div class="flex justify-between items-center">
				{#if step > 1}
					<button
						class="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
						on:click={() => step--}
					>
						← {$i18n.t('Back')}
					</button>
				{:else}
					<div></div>
				{/if}

				{#if step < 3}
					<button
						class="px-6 py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white text-sm font-medium rounded-xl transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
						on:click={() => step++}
						disabled={step === 2 && selectedModels.filter(m => m).length < 2}
					>
						{$i18n.t('Continue')} →
					</button>
				{:else}
					<button
						class="px-6 py-2.5 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-700 hover:to-teal-700 text-white text-sm font-medium rounded-xl transition-all shadow-lg shadow-emerald-500/25 hover:shadow-emerald-500/40 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
						on:click={submitHandler}
						disabled={selectedModels.filter(m => m).length < 2 || !prompt.trim()}
					>
						<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="w-4 h-4">
							<path d="M3.105 2.289a.75.75 0 00-.826.95l1.414 4.925A1.5 1.5 0 005.135 9.25h6.115a.75.75 0 010 1.5H5.135a1.5 1.5 0 00-1.442 1.086l-1.414 4.926a.75.75 0 00.826.95 28.896 28.896 0 0015.293-7.154.75.75 0 000-1.115A28.897 28.897 0 003.105 2.289z" />
						</svg>
						{$i18n.t('Start Symposium')}
					</button>
				{/if}
			</div>
		</div>
	</div>
</Modal>

<style>
	/* Custom range slider styling */
	input[type="range"] {
		-webkit-appearance: none;
		appearance: none;
		background: transparent;
	}
	
	input[type="range"]::-webkit-slider-thumb {
		-webkit-appearance: none;
		appearance: none;
		width: 16px;
		height: 16px;
		border-radius: 50%;
		cursor: pointer;
		margin-top: -4px;
	}

	input[type="range"]::-webkit-slider-runnable-track {
		height: 8px;
		border-radius: 4px;
	}
</style>
