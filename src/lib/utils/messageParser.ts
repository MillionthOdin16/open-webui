export const parseTargets = (content: string): string[] => {
	// Matches @name or @"name with spaces"
	const regex = /@(?:"([^"]+)"|([a-zA-Z0-9_.:-]+))/g;
	const targets: string[] = [];
	let match;

	while ((match = regex.exec(content)) !== null) {
		// match[1] is the quoted group, match[2] is the unquoted group
		targets.push(match[1] || match[2]);
	}

	return targets;
};
