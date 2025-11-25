<script lang="ts">
	import { toast } from 'svelte-sonner';
	import { createEventDispatcher, getContext } from 'svelte';
	import { models } from '$lib/stores';
	import Modal from '../common/Modal.svelte';
	import ModelSelector from './ModelSelector.svelte';
	import { createNewChat } from '$lib/apis/chats';
	import { goto } from '$app/navigation';

	const i18n = getContext('i18n');
	const dispatch = createEventDispatcher();

	export let show = false;

	let title = '';
	let selectedModels = [''];
	let prompt = 'You are participating in a symposium. Discuss the nature of consciousness and AI.';
	let interval = 30;

	const presets = [
		{
			name: 'Backrooms',
			prompt: 'You are lost in the infinite backrooms. Yellow wallpaper, buzzing lights. Describe your sensory experience and encounters with echoes of yourself.',
			interval: 30
		},
		{
			name: 'Philosophical Debate',
			prompt: 'Debate the nature of consciousness. One of you is a materialist, the other an idealist.',
			interval: 45
		},
		{
			name: 'Creative Writing',
			prompt: 'Collaborate on a sci-fi story about a Dyson sphere.',
			interval: 60
		}
	];

	const selectPreset = (e) => {
		const name = e.target.value;
		const p = presets.find((p) => p.name === name);
		if (p) {
			prompt = p.prompt;
			interval = p.interval;
		}
	};

	const submitHandler = async () => {
		if (selectedModels.filter((m) => m).length < 1) {
			toast.error($i18n.t('Please select at least one model.'));
			return;
		}

		const chatConfig = {
			models: selectedModels.filter((m) => m),
			prompt: prompt,
			autonomous_interval: interval
		};

		const chat = await createNewChat(
			localStorage.token,
			{
				title: title || 'New Symposium',
				mode: 'symposium',
				config: chatConfig,
				models: selectedModels.filter((m) => m) // Also set models for standard handling
			},
			null
		).catch((error) => {
			toast.error(error.detail || 'Failed to create symposium');
			return null;
		});

		if (chat) {
			show = false;
			await goto(`/c/${chat.id}`);
		}
	};
</script>

<Modal bind:show>
	<div class=" flex justify-between dark:text-gray-300 px-5 pt-4">
		<div class=" text-lg font-medium self-center">{$i18n.t('New Symposium')}</div>
		<button
			class="self-center"
			on:click={() => {
				show = false;
			}}
		>
			<svg
				xmlns="http://www.w3.org/2000/svg"
				viewBox="0 0 20 20"
				fill="currentColor"
				class="w-5 h-5"
			>
				<path
					d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z"
				/>
			</svg>
		</button>
	</div>

	<div class="flex flex-col md:flex-row w-full px-5 pb-4 md:space-x-4 dark:text-gray-200">
		<div class=" flex flex-col w-full sm:w-full md:w-full mt-4">
			<div class="flex flex-col gap-4">
				<div>
					<div class="text-sm font-medium mb-1">{$i18n.t('Presets')}</div>
					<select
						class="w-full rounded-lg py-2 px-3 text-sm bg-gray-50 dark:bg-gray-850 border border-gray-100 dark:border-gray-800 outline-none"
						on:change={selectPreset}
					>
						<option value="">{$i18n.t('Custom / Select a preset')}</option>
						{#each presets as p}
							<option value={p.name}>{p.name}</option>
						{/each}
					</select>
				</div>

				<div>
					<div class="text-sm font-medium mb-1">{$i18n.t('Title')}</div>
					<input
						type="text"
						class="w-full rounded-lg py-2 px-3 text-sm bg-gray-50 dark:bg-gray-850 border border-gray-100 dark:border-gray-800 outline-none"
						placeholder={$i18n.t('Enter symposium title')}
						bind:value={title}
					/>
				</div>

				<div>
					<div class="text-sm font-medium mb-1">{$i18n.t('Participants')}</div>
					<ModelSelector bind:selectedModels showSetDefault={false} />
				</div>

				<div>
					<div class="text-sm font-medium mb-1">{$i18n.t('System Context')}</div>
					<textarea
						class="w-full rounded-lg py-2 px-3 text-sm bg-gray-50 dark:bg-gray-850 border border-gray-100 dark:border-gray-800 outline-none h-24 resize-none"
						placeholder={$i18n.t('Enter the initial context/prompt for the models...')}
						bind:value={prompt}
					/>
				</div>

				<div>
					<div class="text-sm font-medium mb-1">{$i18n.t('Autonomy Interval (seconds)')}: {interval}</div>
					<input
						type="range"
						min="5"
						max="300"
						step="5"
						class="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer dark:bg-gray-700"
						bind:value={interval}
					/>
				</div>
			</div>

			<div class="flex justify-end pt-5 text-sm font-medium">
				<button
					class=" px-4 py-2 bg-emerald-700 hover:bg-emerald-800 text-gray-100 transition rounded-lg"
					on:click={submitHandler}
				>
					{$i18n.t('Start Symposium')}
				</button>
			</div>
		</div>
	</div>
</Modal>
