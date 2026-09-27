// Editorial topic lookup, shared by the map and video search. No model calls.
(function (root) {
    const normalize = value => String(value || '').normalize('NFKC').toLowerCase().replace(/\s+/g, ' ').trim();
    function find(query, points, limit = 6) {
        const q = normalize(query);
        if (!q) return [];
        return points.map(point => {
            const matched = [...new Set(point.keywords.map(normalize))].filter(word => word.length >= 2 && q.includes(word));
            const phrase = point.questions.some(question => normalize(question) === q);
            const titleMatch = normalize(point.display_title).includes(q);
            // Related topics are suggestions, never substitutions for the user's full query.
            return {point, score: matched.reduce((n,w) => n + w.length, 0) + (phrase ? 40 : 0) + (titleMatch ? 8 : 0)};
        }).filter(r => r.score > 0).sort((a,b) => b.score-a.score).slice(0,limit).map(r => r.point);
    }
    root.AIOKKnowledgeSearch = {find};
    if (typeof module !== 'undefined') module.exports = {find};
})(typeof window === 'undefined' ? globalThis : window);
