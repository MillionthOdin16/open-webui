# Symposium Feature: Independent Analysis & Improvement Plan

## 1. Executive Summary

The **Symposium** feature represents a powerful shift from 1-on-1 AI interaction to multi-agent collaboration. The current implementation provides a solid functional foundation: it supports multiple models, turn-taking, basic state management (Active/Listening/Muted), and real-time intervention (Whispers/Triggers).

However, to truly achieve the goal of being "beautiful, functional, intuitive, and awesome," the feature needs to evolve from a "multi-bot chat room" into a **cohesive virtual stage**. The current experience feels like a standard chat with extra backend logic. The "Awesome" factor will come from visualizing the interaction, enriching the bot behaviors (reactions, interruptions), and giving the user more god-like control over the narrative arc.

## 2. User Experience (UX) Analysis

### Strengths
*   **Creation Wizard**: The preset-based wizard (Debate, Creative, etc.) is excellent. It lowers the barrier to entry and inspires use cases.
*   **Sidebar Controls**: Having immediate access to "Whisper" and "Force Speak" is intuitive for power users.

### Weaknesses & Opportunities
*   **Standard Chat Interface**: The symposium takes place in the standard linear chat feed. This fails to convey the "roundtable" or "stage" metaphor.
    *   *Improvement*: Introduce a **"Stage View"** or "Gallery Mode" where active participants are visually represented (e.g., avatars around a table). The current speaker should be spotlighted.
*   **Visual Feedback**: When a bot is "thinking" or "preparing to speak," there is only a subtle status text.
    *   *Improvement*: Richer animations. Show "thinking bubbles" on the specific avatar in the Stage View.
*   **Narrator/Splice Visibility**: The "Narrator Event" is hidden behind a button in the controls.
    *   *Improvement*: Make the "God Mode" input (Narrator) more prominent, perhaps as a distinct input bar distinct from the "User" input.

## 3. Functional Analysis

### Missing Critical Features
*   **Dynamic Moderator**: Currently, turn-taking is either round-robin or tag-based.
    *   *Gap*: Lack of a dedicated "Moderator" role that doesn't just participate but *directs* (e.g., "Bot A, you made a good point, Bot B, what do you think?").
*   **Session Management**:
    *   *Gap*: Presets are hardcoded. Users cannot save their own custom setups (e.g., "My Coding Team") as reusable templates.
*   **Post-Symposium Artifacts**:
    *   *Gap*: The output is just a chat log.
    *   *Opportunity*: Auto-generation of a "Minutes of Meeting" or "Summary" at the end of a session.

## 4. AI & Interaction Dynamics

### Current Limitations
*   **Linear Sequentiality**: Bots speak one after another.
    *   *Issue*: Real conversations have interruptions, overlapping thoughts, and non-verbal agreement.
    *   *Improvement*: Asynchronous "Reactions". A bot should be able to "thumbs up" or "nod" (emit a metadata event) while another is speaking, without breaking the flow.
*   **Context Window Hard Limit**: The sliding window (`context_limit`) simply drops old messages.
    *   *Issue*: In long debates, bots forget the initial premise.
    *   *Improvement*: Implement a "Topic Summary" that persists in the system prompt, constantly updated by a background summarizer.
*   **Prompt Leakage/Repetition**: Bots often get stuck in loops saying "As an AI..." or repeating pleasantries.
    *   *Improvement*: Stronger negative constraints in the system prompt to enforce "Human-like, direct speech" and prevent "I agree with [Name]" loops.

## 5. Technical Architecture Review

*   **Concurrency**: The backend loop uses `asyncio` but generation is strictly serial.
    *   *Optimization*: Pre-fetching or speculative generation could speed up the "conversation" so there is zero latency between speakers.
*   **Resiliency**: If a model API fails, the symposium pauses or retries blindly.
    *   *Fix*: Smarter fallback logic (e.g., skip to next speaker, or auto-switch to a backup model).
*   **Socket.IO Usage**: Good use of events, but payload sizes could grow large with full history. Ensure only deltas are sent where possible.

## 6. The "Wishlist" (Roadmap to Awesome)

### Phase 1: Visual Polish & Immersion (The "Beautiful")
1.  **Stage View Interface**: A toggleable view showing avatars in a circle/grid.
    *   Highlight current speaker.
    *   Dim muted bots.
    *   Visual "Pulse" when a bot is generating.
2.  **Rich Toast Notifications**: When a "Whisper" is sent, show a visual effect flying to the specific bot avatar.

### Phase 2: Functional Depth (The "Functional" & "Intuitive")
1.  **Saved Templates**: Allow users to save their "Custom Symposium" configurations as new Presets.
2.  **The "Conductor" Tool**: A visual timeline editor to queue up the next 3 speakers manually if desired (drag-and-drop turn order).
3.  **Voice Integration**: (If TTS is available) Spatial audio positioning based on where the avatar is on the "Stage".

### Phase 3: Advanced AI (The "Awesome")
1.  **The Moderator Bot**: A special slot for a model that has `function_calling` rights to mute/unmute others and assign turns based on the conversation flow.
2.  **Sub-channels**: Allow two bots to have a "sidebar" conversation (whispering to each other) that the user can see but other bots cannot.
3.  **Critic/Reflector Mode**: A background process that critiques the debate in real-time and injects "Narrator" challenges (e.g., "The audience looks bored, raise the stakes!").

## 7. Conclusion

The Symposium feature is functionally sound but user-interface safe. To make it "awesome," the interface must break free from the constraints of a linear chat log and embrace the theatrical nature of the feature. By giving users "Director" tools (Stage View, Conductor) and giving Bots "Actor" capabilities (Reactions, Sidebar conversations), Symposium can become the killer feature of Open WebUI.
