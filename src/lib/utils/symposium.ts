// Symposium export/import utilities

export interface SymposiumConfig {
    version: string;
    name: string;
    description: string;
    config: {
        models: string[];
        prompt: string;
        autonomous_interval: number;
        context_limit?: number;
        paused?: boolean;
    };
    metadata: {
        created_at: number;
        author?: string;
    };
}

export function exportSymposiumConfig(chat: any, name?: string): SymposiumConfig {
    return {
        version: '1.0',
        name: name || chat.title || 'Symposium Configuration',
        description: `Exported from ${chat.title || 'Untitled Symposium'}`,
        config: {
            models: chat.config?.models || [],
            prompt: chat.config?.prompt || '',
            autonomous_interval: chat.config?.autonomous_interval || 30,
            context_limit: chat.config?.context_limit || 20,
            paused: chat.config?.paused || false
        },
        metadata: {
            created_at: Date.now(),
            author: 'User'
        }
    };
}

export function downloadSymposiumConfig(config: SymposiumConfig) {
    const blob = new Blob([JSON.stringify(config, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${config.name.toLowerCase().replace(/\s+/g, '_')}_config.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}

export function validateSymposiumConfig(config: any): boolean {
    if (!config || typeof config !== 'object') return false;
    if (!config.version || !config.config) return false;
    if (!Array.isArray(config.config.models) || config.config.models.length === 0) return false;
    if (typeof config.config.prompt !== 'string') return false;
    if (typeof config.config.autonomous_interval !== 'number') return false;
    return true;
}

export async function importSymposiumConfig(file: File): Promise<SymposiumConfig> {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = (e) => {
            try {
                const config = JSON.parse(e.target?.result as string);
                if (validateSymposiumConfig(config)) {
                    resolve(config);
                } else {
                    reject(new Error('Invalid symposium configuration file'));
                }
            } catch (error) {
                reject(new Error('Failed to parse configuration file'));
            }
        };
        reader.onerror = () => reject(new Error('Failed to read file'));
        reader.readAsText(file);
    });
}
