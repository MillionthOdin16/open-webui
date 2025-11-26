<script lang="ts">
	import { models, socket } from '$lib/stores';
	import { getContext, onMount, onDestroy } from 'svelte';
	import { WEBUI_API_BASE_URL } from '$lib/constants';
	import SymposiumControls from './SymposiumControls.svelte';
	import Tooltip from '../common/Tooltip.svelte';
	import { toast } from 'svelte-sonner';

	const i18n = getContext('i18n');

	export let chat;

	let symposiumModels = [];
	let modelStatuses = {};
	let selectedAddModel = '';
	let whisperTarget = null;
	let whisperContent = '';

	$: if (chat && chat.config && chat.config.models) {
		symposiumModels = chat.config.models.map((id) => {
			const m = $models.find((m) => m.id === id);
			return m ? m : { id: id, name: id };
		});
	}

	const onSymposiumStatus = (data) => {
		if (data.chat_id === chat.id) {
			modelStatuses[data.model] = data.status;
		}
	};

	const updateParticipants = async (newModels) => {
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
		}
	};

	const addParticipant = () => {
		if (selectedAddModel && !chat.config.models.includes(selectedAddModel)) {
			updateParticipants([...chat.config.models, selectedAddModel]);
			selectedAddModel = '';
		}
	};

	const removeParticipant = (id) => {
		updateParticipants(chat.config.models.filter((m) => m !== id));
	};

	const triggerModel = async (modelId) => {
		await fetch(`${WEBUI_API_BASE_URL}/chats/${chat.id}/symposium/trigger`, {
			method: 'POST',
			headers: {
				'Content-Type': 'application/json',
				authorization: `Bearer ${localStorage.token}`
			},
			body: JSON.stringify({ model_id: modelId })
		});
	};

	const sendWhisper = async () => {
		if (!whisperTarget || !whisperContent) return;
		const res = await fetch(`${WEBUI_API_BASE_URL}/chats/${chat.id}/symposium/whisper`, {
			method: 'POST',
			headers: {
				'Content-Type': 'application/json',
				authorization: `Bearer ${localStorage.token}`
			},
			body: JSON.stringify({ model_id: whisperTarget, content: whisperContent })
		});
		if (res.ok) {
			toast.success($i18n.t('Whisper sent successfully'));
			whisperTarget = null;
			whisperContent = '';
		}
	};

	onMount(() => {
		$socket?.on('symposium:status', onSymposiumStatus);
	});

	onDestroy(() => {
		$socket?.off('symposium:status', onSymposiumStatus);
	});
</script>

<div
	class="h-full w-full bg-gray-50 dark:bg-gray-900 border-l border-gray-200 dark:border-gray-800 flex flex-col"
>
	<div class="p-4 border-b border-gray-200 dark:border-gray-800 font-medium flex justify-between">
		<div>{$i18n.t('Symposium Models')}</div>
	</div>

	<div class="p-2 border-b border-gray-200 dark:border-gray-800">
		<div class="flex space-x-2">
			<select
				class="flex-1 text-xs rounded-lg border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 dark:text-white"
				bind:value={selectedAddModel}
			>
				<option value="">{$i18n.t('Add Model...')}</option>
				{#each $models.filter((m) => !chat.config.models.includes(m.id)) as model}
					<option value={model.id}>{model.name}</option>
				{/each}
			</select>
			<button
				class="px-2 py-1 bg-emerald-100 text-emerald-800 dark:bg-emerald-900 dark:text-emerald-200 text-xs rounded-lg"
				on:click={addParticipant}
				disabled={!selectedAddModel}
			>
				+
			</button>
		</div>
	</div>

	<div class="flex-1 overflow-y-auto p-4 space-y-4">
		{#each symposiumModels as model}
			<div class="flex flex-col group">
				<div class="flex items-center justify-between">
					<div class="flex items-center space-x-3 overflow-hidden">
						<img
							src={model.info?.meta?.profile_image_url ??
								(model.id
									? `${WEBUI_API_BASE_URL}/models/model/profile/image?id=${model.id}&lang=${$i18n.language}`
									: '/favicon.png')}
							alt={model.name}
							class="w-8 h-8 rounded-full object-cover shrink-0"
						/>
						<div class="text-sm truncate">
							<div class="font-medium truncate">{model.name}</div>
							{#if modelStatuses[model.id]}
								<div class="text-xs text-blue-500 animate-pulse font-medium">
									{modelStatuses[model.id]}...
								</div>
							{/if}
						</div>
					</div>

					<div
						class="flex space-x-1 opacity-0 group-hover:opacity-100 transition-opacity"
					>
						<Tooltip content={$i18n.t('Whisper')}>
							<button
								class="p-1 rounded-full hover:bg-gray-200 dark:hover:bg-gray-800 text-gray-500"
								on:click={() => {
									whisperTarget = whisperTarget === model.id ? null : model.id;
								}}
							>
								<svg
									xmlns="http://www.w3.org/2000/svg"
									viewBox="0 0 20 20"
									fill="currentColor"
									class="w-3.5 h-3.5"
								>
									<path
										fill-rule="evenodd"
										d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z"
										clip-rule="evenodd"
									/>
								</svg>
							</button>
						</Tooltip>
						<Tooltip content={$i18n.t('Force next')}>
							<button
								class="p-1 rounded-full hover:bg-gray-200 dark:hover:bg-gray-800 text-gray-500"
								on:click={() => triggerModel(model.id)}
							>
								<svg
									xmlns="http://www.w3.org/2000/svg"
									viewBox="0 0 20 20"
									fill="currentColor"
									class="w-3.5 h-3.5"
								>
									<path
										fill-rule="evenodd"
										d="M2 10a8 8 0 1116 0 8 8 0 01-16 0zm6.39-2.9a.75.75 0 011.12-.672l4.5 2.5a.75.75 0 010 1.344l-4.5 2.5a.75.75 0 01-1.12-.672V7.1z"
										clip-rule="evenodd"
									/>
								</svg>
							</button>
						</Tooltip>
						<Tooltip content={$i18n.t('Remove')}>
							<button
								class="p-1 rounded-full hover:bg-red-100 dark:hover:bg-red-900/30 text-red-500"
								on:click={() => removeParticipant(model.id)}
							>
								<svg
									xmlns="http://www.w3.org/2000/svg"
									viewBox="0 0 20 20"
									fill="currentColor"
									class="w-3.5 h-3.5"
								>
									<path
										d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z"
									/>
								</svg>
							</button>
						</Tooltip>
					</div>
				</div>

				{#if whisperTarget === model.id}
					<div class="mt-2 p-2 bg-gray-100 dark:bg-gray-800 rounded-lg">
						<div class="text-xs text-gray-500 mb-1">
							{$i18n.t('Whisper to')}
							{model.name}
						</div>
						<textarea
							class="w-full h-16 text-xs p-1.5 rounded border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 resize-none outline-none"
							placeholder={$i18n.t('Enter private instruction...')}
							bind:value={whisperContent}
						/>
						<div class="flex justify-end mt-1">
							<button
								class="px-2 py-1 bg-blue-500 text-white text-xs rounded hover:bg-blue-600"
								on:click={sendWhisper}
							>
								{$i18n.t('Send')}
							</button>
						</div>
					</div>
				{/if}
			</div>
		{/each}
	</div>

	<div class="mt-auto">
		<SymposiumControls {chat} />
	</div>
</div>
