<script lang="ts">
	import { v4 as uuidv4 } from 'uuid';
	import {
		chats,
		config,
		models,
		settings,
		socket,
		user as _user,
		mobile,
		currentChatPage,
		temporaryChatEnabled
	} from '$lib/stores';
	import SymposiumStatusBar from './SymposiumStatusBar.svelte';
	import SymposiumStage from './SymposiumStage.svelte';
	import { tick, getContext, onMount, onDestroy, createEventDispatcher } from 'svelte';
	const dispatch = createEventDispatcher();

	import { toast } from 'svelte-sonner';
	import { getChatList, updateChatById } from '$lib/apis/chats';
	import { copyToClipboard, extractCurlyBraceWords } from '$lib/utils';

	import Message from './Messages/Message.svelte';
	import Loader from '../common/Loader.svelte';
	import Spinner from '../common/Spinner.svelte';

	import ChatPlaceholder from './ChatPlaceholder.svelte';

	const i18n = getContext('i18n');

	export let className = 'h-full flex pt-8';

	export let chatId = '';
	export let user = $_user;

	export let prompt;
	export let history = {};
	export let selectedModels;
	export let atSelectedModel;

	let messages = [];

	export let setInputText: Function = () => {};

	export let sendMessage: Function;
	export let continueResponse: Function;
	export let regenerateResponse: Function;
	export let mergeResponses: Function;

	export let chatActionHandler: Function;
	export let showMessage: Function = () => {};
	export let submitMessage: Function = () => {};
	export let addMessages: Function = () => {};

	export let readOnly = false;
	export let editCodeBlock = true;

	export let topPadding = false;
	export let bottomPadding = false;
	export let autoScroll;

	export let onSelect = (e) => {};
	export let isSymposium = false;

	export let messagesCount: number | null = 20;
	let messagesLoading = false;

	let symposiumStatus = null;
	let symposiumModel = null;
	let symposiumPaused = false;
	let symposiumInterval = 30;
	let symposiumParticipants: string[] = [];

	$: symposiumModelName = $models.find((m) => m.id === symposiumModel)?.name || symposiumModel;

	const onSymposiumStatus = (data) => {
		if (data.chat_id === chatId) {
			if (data.status) {
				symposiumStatus = data.status;
				symposiumModel = data.model;
				if (autoScroll) setTimeout(() => scrollToBottom(), 0);
			} else {
				symposiumStatus = null;
				symposiumModel = null;
			}
		}
	};

	// Update symposium config from chat
	$: if ($chats) {
		const currentChat = $chats.find((c) => c.id === chatId);
		if (currentChat?.config) {
			symposiumPaused = currentChat.config.paused || false;
			symposiumInterval = currentChat.config.autonomous_interval || 30;
			symposiumParticipants = currentChat.config.models || [];
		}
	}

	onMount(() => {
		$socket?.on('symposium:status', onSymposiumStatus);
	});

	onDestroy(() => {
		$socket?.off('symposium:status', onSymposiumStatus);
	});

	const loadMoreMessages = async () => {
		// scroll slightly down to disable continuous loading
		const element = document.getElementById('messages-container');
		element.scrollTop = element.scrollTop + 100;

		messagesLoading = true;
		messagesCount += 20;

		await tick();

		messagesLoading = false;
	};

	$: if (history.currentId) {
		let _messages = [];

		let message = history.messages[history.currentId];
		while (message && (messagesCount !== null ? _messages.length <= messagesCount : true)) {
			_messages.unshift({ ...message });
			message = message.parentId !== null ? history.messages[message.parentId] : null;
		}

		messages = _messages;
	} else {
		messages = [];
	}

	$: if (autoScroll && bottomPadding) {
		(async () => {
			await tick();
			scrollToBottom();
		})();
	}

	const scrollToBottom = () => {
		const element = document.getElementById('messages-container');
		element.scrollTop = element.scrollHeight;
	};

	const updateChat = async () => {
		if (!$temporaryChatEnabled) {
			history = history;
			await tick();
			await updateChatById(localStorage.token, chatId, {
				history: history,
				messages: messages
			});

			currentChatPage.set(1);
			await chats.set(await getChatList(localStorage.token, $currentChatPage));
		}
	};

	const gotoMessage = async (message, idx) => {
		// Determine the correct sibling list (either parent's children or root messages)
		let siblings;
		if (message.parentId !== null) {
			siblings = history.messages[message.parentId].childrenIds;
		} else {
			siblings = Object.values(history.messages)
				.filter((msg) => msg.parentId === null)
				.map((msg) => msg.id);
		}

		// Clamp index to a valid range
		idx = Math.max(0, Math.min(idx, siblings.length - 1));

		let messageId = siblings[idx];

		// If we're navigating to a different message
		if (message.id !== messageId) {
			// Drill down to the deepest child of that branch
			let messageChildrenIds = history.messages[messageId].childrenIds;
			while (messageChildrenIds.length !== 0) {
				messageId = messageChildrenIds.at(-1);
				messageChildrenIds = history.messages[messageId].childrenIds;
			}

			history.currentId = messageId;
		}

		await tick();

		// Optional auto-scroll
		if ($settings?.scrollOnBranchChange ?? true) {
			const element = document.getElementById('messages-container');
			autoScroll = element.scrollHeight - element.scrollTop <= element.clientHeight + 50;

			setTimeout(() => {
				scrollToBottom();
			}, 100);
		}
	};

	const showPreviousMessage = async (message) => {
		if (message.parentId !== null) {
			let messageId =
				history.messages[message.parentId].childrenIds[
					Math.max(history.messages[message.parentId].childrenIds.indexOf(message.id) - 1, 0)
				];

			if (message.id !== messageId) {
				let messageChildrenIds = history.messages[messageId].childrenIds;

				while (messageChildrenIds.length !== 0) {
					messageId = messageChildrenIds.at(-1);
					messageChildrenIds = history.messages[messageId].childrenIds;
				}

				history.currentId = messageId;
			}
		} else {
			let childrenIds = Object.values(history.messages)
				.filter((message) => message.parentId === null)
				.map((message) => message.id);
			let messageId = childrenIds[Math.max(childrenIds.indexOf(message.id) - 1, 0)];

			if (message.id !== messageId) {
				let messageChildrenIds = history.messages[messageId].childrenIds;

				while (messageChildrenIds.length !== 0) {
					messageId = messageChildrenIds.at(-1);
					messageChildrenIds = history.messages[messageId].childrenIds;
				}

				history.currentId = messageId;
			}
		}

		await tick();

		if ($settings?.scrollOnBranchChange ?? true) {
			const element = document.getElementById('messages-container');
			autoScroll = element.scrollHeight - element.scrollTop <= element.clientHeight + 50;

			setTimeout(() => {
				scrollToBottom();
			}, 100);
		}
	};

	const showNextMessage = async (message) => {
		if (message.parentId !== null) {
			let messageId =
				history.messages[message.parentId].childrenIds[
					Math.min(
						history.messages[message.parentId].childrenIds.indexOf(message.id) + 1,
						history.messages[message.parentId].childrenIds.length - 1
					)
				];

			if (message.id !== messageId) {
				let messageChildrenIds = history.messages[messageId].childrenIds;

				while (messageChildrenIds.length !== 0) {
					messageId = messageChildrenIds.at(-1);
					messageChildrenIds = history.messages[messageId].childrenIds;
				}

				history.currentId = messageId;
			}
		} else {
			let childrenIds = Object.values(history.messages)
				.filter((message) => message.parentId === null)
				.map((message) => message.id);
			let messageId =
				childrenIds[Math.min(childrenIds.indexOf(message.id) + 1, childrenIds.length - 1)];

			if (message.id !== messageId) {
				let messageChildrenIds = history.messages[messageId].childrenIds;

				while (messageChildrenIds.length !== 0) {
					messageId = messageChildrenIds.at(-1);
					messageChildrenIds = history.messages[messageId].childrenIds;
				}

				history.currentId = messageId;
			}
		}

		await tick();

		if ($settings?.scrollOnBranchChange ?? true) {
			const element = document.getElementById('messages-container');
			autoScroll = element.scrollHeight - element.scrollTop <= element.clientHeight + 50;

			setTimeout(() => {
				scrollToBottom();
			}, 100);
		}
	};

	const rateMessage = async (messageId, rating) => {
		history.messages[messageId].annotation = {
			...history.messages[messageId].annotation,
			rating: rating
		};

		await updateChat();
	};

	const editMessage = async (messageId, { content, files }, submit = true) => {
		if ((selectedModels ?? []).filter((id) => id).length === 0) {
			toast.error($i18n.t('Model not selected'));
			return;
		}
		if (history.messages[messageId].role === 'user') {
			if (submit) {
				// New user message
				let userPrompt = content;
				let userMessageId = uuidv4();

				let userMessage = {
					id: userMessageId,
					parentId: history.messages[messageId].parentId,
					childrenIds: [],
					role: 'user',
					content: userPrompt,
					...(files && { files: files }),
					models: selectedModels,
					timestamp: Math.floor(Date.now() / 1000) // Unix epoch
				};

				let messageParentId = history.messages[messageId].parentId;

				if (messageParentId !== null) {
					history.messages[messageParentId].childrenIds = [
						...history.messages[messageParentId].childrenIds,
						userMessageId
					];
				}

				history.messages[userMessageId] = userMessage;
				history.currentId = userMessageId;

				await tick();
				await sendMessage(history, userMessageId);
			} else {
				// Edit user message
				history.messages[messageId].content = content;
				history.messages[messageId].files = files;
				await updateChat();
			}
		} else {
			if (submit) {
				// New response message
				const responseMessageId = uuidv4();
				const message = history.messages[messageId];
				const parentId = message.parentId;

				const responseMessage = {
					...message,
					id: responseMessageId,
					parentId: parentId,
					childrenIds: [],
					files: undefined,
					content: content,
					timestamp: Math.floor(Date.now() / 1000) // Unix epoch
				};

				history.messages[responseMessageId] = responseMessage;
				history.currentId = responseMessageId;

				// Append messageId to childrenIds of parent message
				if (parentId !== null) {
					history.messages[parentId].childrenIds = [
						...history.messages[parentId].childrenIds,
						responseMessageId
					];
				}

				await updateChat();
			} else {
				// Edit response message
				history.messages[messageId].originalContent = history.messages[messageId].content;
				history.messages[messageId].content = content;
				await updateChat();
			}
		}
	};

	const actionMessage = async (actionId, message, event = null) => {
		await chatActionHandler(chatId, actionId, message.model, message.id, event);
	};

	const saveMessage = async (messageId, message) => {
		history.messages[messageId] = message;
		await updateChat();
	};

	const deleteMessage = async (messageId) => {
		const messageToDelete = history.messages[messageId];
		const parentMessageId = messageToDelete.parentId;
		const childMessageIds = messageToDelete.childrenIds ?? [];

		// Collect all grandchildren
		const grandchildrenIds = childMessageIds.flatMap(
			(childId) => history.messages[childId]?.childrenIds ?? []
		);

		// Update parent's children
		if (parentMessageId && history.messages[parentMessageId]) {
			history.messages[parentMessageId].childrenIds = [
				...history.messages[parentMessageId].childrenIds.filter((id) => id !== messageId),
				...grandchildrenIds
			];
		}

		// Update grandchildren's parent
		grandchildrenIds.forEach((grandchildId) => {
			if (history.messages[grandchildId]) {
				history.messages[grandchildId].parentId = parentMessageId;
			}
		});

		// Delete the message and its children
		[messageId, ...childMessageIds].forEach((id) => {
			delete history.messages[id];
		});

		await tick();

		showMessage({ id: parentMessageId });

		// Update the chat
		await updateChat();
	};

	const triggerScroll = () => {
		if (autoScroll) {
			const element = document.getElementById('messages-container');
			autoScroll = element.scrollHeight - element.scrollTop <= element.clientHeight + 50;
			setTimeout(() => {
				scrollToBottom();
			}, 100);
		}
	};
</script>

<div class={className}>
	{#if Object.keys(history?.messages ?? {}).length == 0}
		<ChatPlaceholder modelIds={selectedModels} {atSelectedModel} {onSelect} />
	{:else}
		<div class="w-full pt-2">
			{#key chatId}
				<section class="w-full" aria-labelledby="chat-conversation">
					<h2 class="sr-only" id="chat-conversation">{$i18n.t('Chat Conversation')}</h2>

					<!-- Symposium Stage View -->
					{#if symposiumParticipants.length > 0}
						<SymposiumStage
							chat={{
								id: chatId,
								config: {
									models: symposiumParticipants
								}
							}}
						/>
					{/if}

					{#if messages.at(0)?.parentId !== null}
						<Loader
							on:visible={(e) => {
								console.log('visible');
								if (!messagesLoading) {
									loadMoreMessages();
								}
							}}
						>
							<div class="w-full flex justify-center py-1 text-xs animate-pulse items-center gap-2">
								<Spinner className=" size-4" />
								<div class=" ">{$i18n.t('Loading...')}</div>
							</div>
						</Loader>
					{/if}
					<ul role="log" aria-live="polite" aria-relevant="additions" aria-atomic="false">
						{#each messages as message, messageIdx (message.id)}
							<Message
								{chatId}
								bind:history
								{selectedModels}
								messageId={message.id}
								idx={messageIdx}
								{user}
								{setInputText}
								{gotoMessage}
								{showPreviousMessage}
								{showNextMessage}
								{updateChat}
								{editMessage}
								{deleteMessage}
								{rateMessage}
								{actionMessage}
								{saveMessage}
								{submitMessage}
								{regenerateResponse}
								{continueResponse}
								{mergeResponses}
								{addMessages}
								{triggerScroll}
								{readOnly}
								{editCodeBlock}
								{topPadding}
								{isSymposium}
							/>
						{/each}

						{#if symposiumStatus && symposiumModel}
							{@const speakingModel = $models.find(m => m.id === symposiumModel)}
							<li class="flex flex-col justify-between px-5 mb-3 w-full max-w-5xl mx-auto">
								<div class="flex items-center gap-3 p-4 rounded-2xl bg-gradient-to-r from-emerald-50 to-teal-50 dark:from-emerald-900/20 dark:to-teal-900/20 border border-emerald-200/50 dark:border-emerald-800/50">
									<div class="relative flex-shrink-0">
										<img
											src={speakingModel?.info?.meta?.profile_image_url || `/api/models/model/profile/image?id=${symposiumModel}`}
											alt={symposiumModelName}
											class="w-10 h-10 rounded-full object-cover ring-2 ring-emerald-500 ring-offset-2 ring-offset-white dark:ring-offset-gray-900"
										/>
										<div class="absolute -bottom-1 -right-1 w-5 h-5 bg-emerald-500 rounded-full flex items-center justify-center">
											<svg class="w-3 h-3 text-white animate-spin" fill="none" viewBox="0 0 24 24">
												<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
												<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
											</svg>
										</div>
									</div>
									<div class="flex-1">
										<div class="flex items-center gap-2">
											<span class="font-semibold text-gray-900 dark:text-white">{symposiumModelName}</span>
											<span class="text-xs px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-700 dark:bg-emerald-900/50 dark:text-emerald-300">
												{symposiumStatus}
											</span>
										</div>
										<div class="flex items-center gap-2 mt-1">
											<div class="flex gap-1">
												<div class="w-2 h-2 bg-emerald-500 rounded-full animate-bounce" style="animation-delay: 0s;"></div>
												<div class="w-2 h-2 bg-emerald-500 rounded-full animate-bounce" style="animation-delay: 0.15s;"></div>
												<div class="w-2 h-2 bg-emerald-500 rounded-full animate-bounce" style="animation-delay: 0.3s;"></div>
											</div>
											<span class="text-sm text-gray-500 dark:text-gray-400">{$i18n.t('Composing response...')}</span>
										</div>
									</div>
								</div>
							</li>
						{/if}
					</ul>
				</section>
				<div class="pb-18"></div>
				{#if bottomPadding}
					<div class="  pb-6"></div>
				{/if}
			{/key}
		</div>
	{/if}
</div>
