<script lang="ts">
	import { getContext } from 'svelte';
	import { models, chatId, chats, currentChatPage } from '$lib/stores';
	import Tooltip from '../common/Tooltip.svelte';
	import Sparkles from '../icons/Sparkles.svelte';
    import Pause from '../icons/Pause.svelte';
    import Play from '../icons/Play.svelte';
    import { updateChatById, getChatList } from '$lib/apis/chats';

	const i18n = getContext('i18n');

	export let chat;
	export let selectedModels = [];

    const toggleActive = async () => {
        const active = !(chat?.config?.active ?? true);
        const config = {
            ...(chat.config ?? {}),
            active: active
        };

        // We need to update the chat config.
        // Using updateChatById which calls /chats/{id}
        // The backend update_chat_by_id endpoint now supports updating config via the `config` field in ChatForm if we send it.
        // But `updateChatById` in `$lib/apis/chats` usually sends `chat` object.
        // Let's check if we need to update `chat.config` inside the `chat` object or as a separate field.
        // Our modified backend endpoint uses `form_data.config` if present.

        // We'll update the local chat object first for optimism
        chat.config = config;

        const res = await updateChatById(localStorage.token, chat.id, {
            chat: chat.chat, // Keep existing chat data
            config: config
        });

        if (res) {
            chat = res;
            // Refresh list to ensure state consistency if needed
            // chats.set(await getChatList(localStorage.token, $currentChatPage));
        }
    };
</script>

<div class="h-full w-64 flex-none flex flex-col border-l dark:border-gray-800 bg-gray-50 dark:bg-gray-900">
	<div class="px-4 py-3 border-b dark:border-gray-800 flex items-center justify-between">
		<h3 class="font-medium text-sm">{$i18n.t('Symposium')}</h3>
		<div class="flex items-center gap-2">
            <div class="text-xs text-gray-500">
                {#if (chat?.config?.active ?? true)}
                    <span class="flex items-center gap-1 text-green-500">
                        <span class="relative flex h-2 w-2">
                            <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
                            <span class="relative inline-flex rounded-full h-2 w-2 bg-green-500"></span>
                        </span>
                        {$i18n.t('Active')}
                    </span>
                {:else}
                    <span class="text-gray-400">{$i18n.t('Paused')}</span>
                {/if}
            </div>

            <Tooltip content={(chat?.config?.active ?? true) ? $i18n.t('Pause') : $i18n.t('Resume')}>
                <button
                    class="p-1 rounded-full hover:bg-gray-200 dark:hover:bg-gray-700 transition"
                    on:click={toggleActive}
                >
                    {#if (chat?.config?.active ?? true)}
                        <Pause className="size-3.5" />
                    {:else}
                        <Play className="size-3.5" />
                    {/if}
                </button>
            </Tooltip>
        </div>
	</div>

	<div class="flex-1 overflow-y-auto p-2 space-y-2">
		{#each selectedModels as modelId}
			{@const model = $models.find((m) => m.id === modelId)}
			{#if model}
				<div class="flex items-center gap-2 p-2 rounded-lg bg-white dark:bg-gray-800 border dark:border-gray-700 shadow-xs">
					<img
						src={model?.info?.meta?.profile_image_url ?? '/static/favicon.png'}
						alt={model?.name}
						class="size-8 rounded-full object-cover"
					/>
					<div class="flex-1 min-w-0">
						<div class="font-medium text-sm truncate">{model?.name}</div>
						<div class="text-xs text-gray-500 truncate">
							{modelId}
						</div>
					</div>
                    <!-- TODO: Add status indicator if speaking -->
				</div>
			{/if}
		{/each}
	</div>

    <div class="p-3 border-t dark:border-gray-800 text-xs text-gray-500 text-center">
        {$i18n.t('Models will respond autonomously.')}
    </div>
</div>
