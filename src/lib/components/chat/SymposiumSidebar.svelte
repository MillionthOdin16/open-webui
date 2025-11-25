<script lang="ts">
	import { models, socket } from '$lib/stores';
	import { getContext, onMount, onDestroy } from 'svelte';
	import { WEBUI_API_BASE_URL } from '$lib/constants';
	import SymposiumControls from './SymposiumControls.svelte';
	import Tooltip from '../common/Tooltip.svelte';

	const i18n = getContext('i18n');

	export let chat;

	let symposiumModels = [];
	let modelStatuses = {};

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
	<div class="p-4 border-b border-gray-200 dark:border-gray-800 font-medium">
		{$i18n.t('Symposium Models')}
	</div>
	<div class="flex-1 overflow-y-auto p-4 space-y-4">
		{#each symposiumModels as model}
			<div class="flex items-center justify-between group">
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

				<Tooltip content={$i18n.t('Force next speaker')}>
					<button
						class="p-1.5 rounded-full hover:bg-gray-200 dark:hover:bg-gray-800 text-gray-500 opacity-0 group-hover:opacity-100 transition-opacity"
						on:click={() => triggerModel(model.id)}
					>
						<svg
							xmlns="http://www.w3.org/2000/svg"
							viewBox="0 0 20 20"
							fill="currentColor"
							class="w-4 h-4"
						>
							<path
								fill-rule="evenodd"
								d="M2 10a8 8 0 1116 0 8 8 0 01-16 0zm6.39-2.9a.75.75 0 011.12-.672l4.5 2.5a.75.75 0 010 1.344l-4.5 2.5a.75.75 0 01-1.12-.672V7.1z"
								clip-rule="evenodd"
							/>
						</svg>
					</button>
				</Tooltip>
			</div>
		{/each}
	</div>

	<div class="mt-auto">
		<SymposiumControls {chat} />
	</div>
</div>
