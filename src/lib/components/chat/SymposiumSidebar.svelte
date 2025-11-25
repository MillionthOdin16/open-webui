<script lang="ts">
	import { models } from '$lib/stores';
	import { getContext } from 'svelte';
	import { WEBUI_API_BASE_URL } from '$lib/constants';

	const i18n = getContext('i18n');

	export let chat;

	let symposiumModels = [];

	$: if (chat && chat.config && chat.config.models) {
		symposiumModels = chat.config.models.map((id) => {
			const m = $models.find((m) => m.id === id);
			return m ? m : { id: id, name: id };
		});
	}
</script>

<div
	class="h-full w-full bg-gray-50 dark:bg-gray-900 border-l border-gray-200 dark:border-gray-800 flex flex-col"
>
	<div class="p-4 border-b border-gray-200 dark:border-gray-800 font-medium">
		{$i18n.t('Symposium Models')}
	</div>
	<div class="flex-1 overflow-y-auto p-4 space-y-4">
		{#each symposiumModels as model}
			<div class="flex items-center space-x-3">
				<img
					src={model.info?.meta?.profile_image_url ??
						(model.id
							? `${WEBUI_API_BASE_URL}/models/model/profile/image?id=${model.id}&lang=${$i18n.language}`
							: '/favicon.png')}
					alt={model.name}
					class="w-8 h-8 rounded-full object-cover"
				/>
				<div class="text-sm">
					<div class="font-medium">{model.name}</div>
				</div>
			</div>
		{/each}
	</div>
</div>
