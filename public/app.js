document.addEventListener('DOMContentLoaded', () => {
    const searchInput = document.getElementById('searchInput');
    const searchBtn = document.getElementById('searchBtn');
    const clearBtn = document.getElementById('clearBtn');
    const btnText = document.getElementById('btnText');
    const categoryTabs = document.getElementById('categoryTabs');
    const videoGrid = document.getElementById('videoGrid');
    const sectionTitle = document.getElementById('sectionTitle');
    const resultCount = document.getElementById('resultCount');
    const searchInterpretation = document.getElementById('searchInterpretation');
    const hotTags = document.querySelectorAll('.tag-pill');
    const loadingOverlay = document.getElementById('loadingOverlay');
    const themeToggleBtn = document.getElementById('themeToggleBtn');
    const randomBtn = document.getElementById('randomBtn');
    const htmlEl = document.documentElement;

    let currentCategory = 'all';
    let encyclopediaData = null;
    let isSearching = false;
    let searchGeneration = 0;
    let knowledgePromise = null;

    let lastSearchQuery = '';
    let currentRawSearchResults = null;
    const shardCache = new Map();
    const MAX_CACHED_SHARDS = 24;
    const MAX_SEARCH_RESULTS = 80;
    const MAX_SUMMARY_RECALL_VIDEOS = 24;
    let videosById = null;
    const paragraphShardCache = new Map();
    const MAX_CACHED_PARAGRAPH_SHARDS = 32;

    // These are spelling and naming aliases, not broad topical associations.
    // A search for "GR3 街拍" must not be satisfied by a video that mentions
    // only street photography.  Related concepts (for example ISO and noise)
    // stay separate so multi-term queries retain their AND meaning.
    const SEARCH_ALIASES = {
        'iso': ['iso', '感光度'],
        '高感': ['高感', '高iso', '高 iso', '高感光度'],
        '自動iso': ['自動iso', '自動 iso', 'auto iso', 'iso auto'],
        '噪點': ['噪點', '雜訊'],
        '光圈': ['光圈', 'aperture', 'f值'],
        '光圈先決': ['光圈先決', '光圈優先', 'aperture priority'],
        '景深': ['景深', 'depth of field'],
        '虛化': ['虛化', '背景虛化'],
        '雜亂': ['雜亂', '凌亂', '很亂', '太亂'],
        '快門': ['快門', 'shutter', '快門速度'],
        '快門先決': ['快門先決', '快門優先', 'shutter priority'],
        '慢快門': ['慢快門', '慢速快門'],
        '長曝': ['長曝', '長時間曝光'],
        '底片': ['底片', '膠片', '膠卷'],
        '底片模擬': ['底片模擬', 'film simulation'],
        '對焦': ['對焦', 'focus', '自動對焦', 'af'],
        '自動對焦': ['自動對焦', 'af'],
        'afc': ['afc', 'af-c', 'af c', '連續自動對焦'],
        'afs': ['afs', 'af-s', 'af s', '單次自動對焦'],
        'ael': ['ael', 'ae-l', 'ae l', '曝光鎖定'],
        'afl': ['afl', 'af-l', 'af l', '對焦鎖定', '對焦鎖'],
        'afon': ['afon', 'af-on', 'af on', '背鍵對焦'],
        // 追焦 is used for both AF tracking and panning in this channel.
        '追焦': ['追焦', '連續對焦', '連續自動對焦', 'afc', 'af-c', 'af c', 'fc'],
        '連續對焦': ['連續對焦', '連續自動對焦', 'afc', 'af-c', 'af c', 'fc'],
        '中央重點測光': ['中央重點測光', '中央重點側光'],
        '矩陣測光': ['矩陣測光', '矩陣側光'],
        '離機閃燈': ['離機閃燈', '離機閃', '離閃', '離機的閃光燈'],
        '引閃器': ['引閃器', '觸發器'],
        '鳥類攝影': ['鳥類攝影', '拍鳥'],
        '搖攝': ['搖攝', '追焦照', '追焦橫向', '跟著車子移動'],
        '滾動快門': ['滾動快門', '果凍效應'],
        '兒童': ['兒童', '小孩子', '小孩', '孩子'],
        '夜拍': ['夜拍', '夜間拍攝', '晚上拍', '晚上看星空'],
        '眼對焦': ['眼對焦', '眼部對焦'],
        '眩光': ['眩光', '炫光', '耀光', 'lens flare'],
        '畸變': ['畸變', '桶狀變形', '枕狀變形', '鏡頭變形', 'lens distortion'],
        '解像力': ['解像力', '解析力'],
        '銳利度': ['銳利度', '銳度'],
        '白平衡': ['白平衡', 'white balance', 'wb'],
        '全片幅': ['全片幅', '全畫幅', 'full frame', 'fullframe'],
        '中片幅': ['中片幅', '中畫幅', 'medium format'],
        'm43': ['m43', 'm4/3', 'micro four thirds', 'micro 4/3'],
        '機身防手震': ['機身防手震', '機身防抖', 'ibis'],
        '鏡頭防手震': ['鏡頭防手震', '鏡頭防抖', 'ois'],
        'evf': ['evf', '電子觀景窗', '電子觀景器'],
        'ovf': ['ovf', '光學觀景窗', '光學觀景器'],
        '富士': ['富士', 'fuji', 'fujifilm'],
        '索尼': ['索尼', 'sony'],
        '尼康': ['尼康', 'nikon'],
        'ricoh': ['ricoh', '理光'],
        '佳能': ['佳能', 'canon'],
        '萊卡': ['萊卡', '徠卡', 'leica'],
        '蔡司': ['蔡司', 'zeiss', 'carl zeiss'],
        'sigma': ['sigma', '適馬'],
        'tamron': ['tamron', '騰龍'],
        'panasonic': ['panasonic', '松下'],
        'olympus': ['olympus', '奧林巴斯', 'om system', 'omsystem'],
        'dji': ['dji', '大疆'],
        'gopro': ['gopro', 'go pro'],
        'cpl': ['cpl', '偏光鏡', '偏振鏡'],
        'nd': ['nd', '減光鏡'],
        '街拍': ['街拍', '快照', 'snap', 'street photography', '掃街', '抓拍'],
        '調色': ['調色', 'color grading'],
        '遮色片': ['遮色片', '蒙版', 'mask'],
        '達芬奇': ['達芬奇', 'davinci resolve', 'davinci', 'resolve'],
        '8bit': ['8bit', '8 bit', '8-bit'],
        '10bit': ['10bit', '10 bit', '10-bit'],
        'adobergb': ['adobergb', 'adobe rgb', 'adobe-rgb'],
        '鏡頭': ['鏡頭', 'lens'],
        'a73': ['a73', 'a7iii', 'a7 iii', 'a7 3'],
        'a74': ['a74', 'a7iv', 'a7 iv', 'a7 4'],
        'a7r3': ['a7r3', 'a7riii', 'a7r iii', 'a7r 3'],
        'a7r4': ['a7r4', 'a7riv', 'a7r iv', 'a7r 4'],
        'a7r5': ['a7r5', 'a7rv', 'a7r v', 'a7r 5'],
        'a7s3': ['a7s3', 'a7siii', 'a7s iii', 'a7s 3'],
        'a7c2': ['a7c2', 'a7cii', 'a7c ii', 'a7c 2'],
        'a92': ['a92', 'a9ii', 'a9 ii', 'a9 2'],
        'a93': ['a93', 'a9iii', 'a9 iii', 'a9 3'],
        'a12': ['a12', 'a1ii', 'a1 ii', 'a1 2'],
        'r52': ['r52', 'r5ii', 'r5 ii', 'r5 2'],
        'r62': ['r62', 'r6ii', 'r6 ii', 'r6 2'],
        '5d4': ['5d4', '5div', '5d iv', '5d 4'],
        'g7x3': ['g7x3', 'g7xiii', 'g7x iii', 'g7x 3'],
        'z62': ['z62', 'z6ii', 'z6 ii', 'z6 2'],
        'z63': ['z63', 'z6iii', 'z6 iii', 'z6 3'],
        'z72': ['z72', 'z7ii', 'z7 ii', 'z7 2'],
        'z52': ['z52', 'z5ii', 'z5 ii', 'z5 2'],
        'x1005': ['x1005', 'x100v', 'x100 v'],
        'x1006': ['x1006', 'x100vi', 'x100 vi', 'x100 6'],
        'xt3': ['xt3', 'x-t3', 'x t3'],
        'xt4': ['xt4', 'x-t4', 'x t4'],
        'xt5': ['xt5', 'x-t5', 'x t5'],
        'gr3': ['gr3', 'griii', 'gr iii', 'gr 3'],
        'gr3x': ['gr3x', 'griiix', 'gr iiix', 'gr 3x']
    };

    const QUERY_NORMALIZATION = {
        '接拍': '街拍',
        'griii': 'gr3',
        'gr iii': 'gr3',
        'gr 3': 'gr3',
        'griiix': 'gr3x',
        'gr iiix': 'gr3x',
        'gr 3x': 'gr3x',
        '理光': 'ricoh'
    };

    const ALIAS_TO_CANONICAL = Object.entries(SEARCH_ALIASES).reduce(
        (aliases, [canonical, terms]) => {
            [canonical, ...terms].forEach(term => {
                aliases[String(term).toLowerCase()] = canonical;
            });
            return aliases;
        },
        {}
    );

    // These are safe building blocks for deliberate unspaced AND queries.
    // They do not expand to synonyms: 前景層次 becomes 前景 + 層次, while an
    // unknown phrase such as 景深合成 remains one literal phrase.
    const COMPOUND_QUERY_TERMS = [
        '構圖', '前景', '背景', '層次', '簡化', '對稱',
        '光影', '焦外', '散景', '低角度', '框架'
    ];

    // A small set of learner phrases denotes two concrete concepts.  Keep
    // each part visible so partial matches are labelled honestly in the UI.
    const COMPOUND_QUERY_OVERRIDES = {
        '環境人像': ['環境', '人像'],
        '兒童攝影': ['兒童', '攝影'],
        '街頭光影': ['街頭', '光影'],
        '風景構圖': ['風景', '構圖'],
        '夜拍對焦': ['夜拍', '對焦'],
        '底片沖洗': ['底片', '沖洗']
    };

    const KNOWN_QUERY_TERMS = [...new Set([
        ...Object.keys(SEARCH_ALIASES),
        ...Object.values(SEARCH_ALIASES).flat(),
        ...Object.keys(QUERY_NORMALIZATION),
        ...COMPOUND_QUERY_TERMS
    ])].sort((a, b) => b.length - a.length);
    const KNOWN_SPACED_QUERY_TERMS = KNOWN_QUERY_TERMS.filter(term => term.includes(' '));

    // Translate common question wording into search topics, never an inferred
    // answer: 對不到焦 means 對焦, not 手動對焦 or 無限遠. An unknown span
    // (including exclusions such as 不要) keeps the original literal query.
    const QUESTION_TOPIC_WORDS = [...new Set([
        ...KNOWN_QUERY_TERMS, '星空', '人像', '手動對焦', '無限遠',
        '水平', '垂直', '逆光', '曝光', '曝光補償'
    ])].sort((a, b) => b.length - a.length);
    const QUESTION_WORDING = [
        '有什麼關係', '怎麼辦', '為什麼', '怎麼樣', '一定要',
        '請問', '怎麼', '如何', '需要', '可以', '照片', '拍攝',
        '以及', '還有', '和', '與', '的', '用', '拍', '要', '嗎', '呢'
    ];
    const QUESTION_SYMPTOMS = ['對不到焦', '對不上焦', '無法對焦'];

    function parseNaturalSearchQuery(query) {
        let remaining = String(query || '').trim().toLowerCase().replace(/\s+/g, ' ');
        const parts = [];
        let hasQuestionWording = false;
        while (remaining) {
            const separator = remaining.match(/^[\s，。！？、；?!,;]+/);
            if (separator) {
                remaining = remaining.slice(separator[0].length);
                continue;
            }
            const symptom = QUESTION_SYMPTOMS.find(word => remaining.startsWith(word));
            const topic = symptom || QUESTION_TOPIC_WORDS.find(word => (
                remaining.startsWith(word)
                && !(/[a-z0-9]$/.test(word) && /^[a-z0-9]/.test(remaining.slice(word.length)))
            )) || remaining.match(/^(?:f\/\d+(?:\.\d+)?|4:2:2|[a-z][a-z0-9]*(?:[./:][a-z0-9]+)*)/)?.[0];
            if (topic) {
                const term = symptom ? '對焦' : normalizeQueryTerm(topic);
                hasQuestionWording ||= Boolean(symptom) || ['很亂', '太亂'].includes(topic);
                if (!parts.some(part => part.term === term)) parts.push({term, label: term});
                if (parts.length > 4) return null;
                remaining = remaining.slice(topic.length);
                continue;
            }
            const wording = QUESTION_WORDING.find(word => remaining.startsWith(word));
            if (!wording) return null;
            hasQuestionWording = true;
            remaining = remaining.slice(wording.length);
        }
        return hasQuestionWording && parts.length ? parts : null;
    }

    function normalizeQueryTerm(term) {
        const normalized = QUERY_NORMALIZATION[term] || term;
        return ALIAS_TO_CANONICAL[normalized] || normalized;
    }

    function splitKnownQueryTokens(query) {
        const source = String(query || '').trim().replace(/\s+/g, ' ');
        const lowerSource = source.toLowerCase();
        const chunks = [];
        let offset = 0;

        while (offset < source.length) {
            while (source[offset] === ' ') offset += 1;
            if (offset >= source.length) break;

            const phrase = KNOWN_SPACED_QUERY_TERMS.find(candidate => {
                if (!lowerSource.startsWith(candidate, offset)) return false;
                const end = offset + candidate.length;
                return end === source.length || source[end] === ' ';
            });
            if (phrase) {
                chunks.push({ label: source.slice(offset, offset + phrase.length), value: phrase });
                offset += phrase.length;
                continue;
            }

            const nextSpace = source.indexOf(' ', offset);
            const end = nextSpace === -1 ? source.length : nextSpace;
            chunks.push({ label: source.slice(offset, end), value: lowerSource.slice(offset, end) });
            offset = end;
        }
        return chunks;
    }

    // Preserve the visitor's wording alongside the canonical lookup term.
    // For example, "GRIII 接拍" becomes [{ term: "gr3", label: "GRIII" },
    // { term: "街拍", label: "接拍" }].  The label is what we show on each
    // result card, so a partial hit can never be presented as the whole query.
    function parseSearchQuery(query) {
        const trimmedQuery = String(query || '').trim();
        const normalizedQuery = trimmedQuery.replace(/\s+/g, ' ').toLowerCase();
        const wholeCanonical = ALIAS_TO_CANONICAL[normalizedQuery];
        if (wholeCanonical) {
            return [{ term: wholeCanonical, label: trimmedQuery }];
        }
        if (COMPOUND_QUERY_OVERRIDES[normalizedQuery]) {
            return COMPOUND_QUERY_OVERRIDES[normalizedQuery].map(term => ({term, label: term}));
        }

        const naturalParts = parseNaturalSearchQuery(trimmedQuery);
        if (naturalParts) return naturalParts;

        const rawTokens = splitKnownQueryTokens(trimmedQuery);
        const parts = [];

        rawTokens.forEach(({ label: rawToken, value }) => {
            const normalized = value.toLowerCase()
                .replace(/^gr\s*iii\s*x$/i, 'gr3x')
                .replace(/^gr\s*iii$/i, 'gr3')
                .replace(/^gr\s*3\s*x$/i, 'gr3x')
                .replace(/^gr\s*3$/i, 'gr3');
            const split = [];
            let remaining = normalized;

            if (ALIAS_TO_CANONICAL[normalized]) {
                split.push(normalizeQueryTerm(normalized));
                remaining = '';
            }

            // ISO3200 and ND1000 are exact parameter values, not two broad
            // concepts. Preserve an unregistered letters+digits token whole;
            // verified paragraph matching still enforces its token boundary.
            if (
                (/^[a-z]+\d+$/.test(normalized) || /^[a-z]{2,4}$/.test(normalized))
                && !KNOWN_QUERY_TERMS.includes(normalized)
            ) {
                split.push(normalized);
                remaining = '';
            }

            if (remaining) {
                const compound = [];
                let compoundRemaining = remaining;
                while (compoundRemaining) {
                    const known = KNOWN_QUERY_TERMS.find(
                        candidate => compoundRemaining.startsWith(candidate)
                    );
                    if (!known) {
                        compound.length = 0;
                        break;
                    }
                    compound.push(normalizeQueryTerm(known));
                    compoundRemaining = compoundRemaining.slice(known.length);
                }

                // Split an unspaced compound only when the whole token is made
                // of known concepts (for example 光圈景深).  If only a prefix
                // is known (景深合成), preserve the complete phrase so generic
                // n-gram lookup can source-verify it literally.
                if (compound.length >= 2) {
                    split.push(...compound);
                } else {
                    split.push(normalizeQueryTerm(remaining));
                }
            }

            split.forEach(term => {
                if (!parts.some(part => part.term === term)) {
                    parts.push({
                        term,
                        // An unspaced compound has no unambiguous raw label for
                        // each part, so use its canonical, readable term instead.
                        label: split.length === 1 ? rawToken : term
                    });
                }
            });
        });

        return parts.slice(0, 4);
    }

    function expandTerms(term) {
        const normalized = normalizeQueryTerm(term.trim().toLowerCase());
        const aliases = [normalized, ...(SEARCH_ALIASES[normalized] || [])];
        return [...new Set(aliases.flatMap(alias => [alias, ...technicalNotationAliases(alias)]))];
    }

    function technicalNotationAliases(term) {
        const source = String(term || '').trim().toLowerCase();
        const aperture = source.match(/^f\s*\/?\s*(\d+(?:\.\d+)?)$/);
        if (aperture) return [`f${aperture[1]}`, `f/${aperture[1]}`];
        if (/^m\s*4\s*\/?\s*3$/.test(source)) return ['m43', 'm4/3'];
        if (/^(?:422|4\s*:\s*2\s*:\s*2)$/.test(source)) return ['422', '4:2:2'];
        return [];
    }

    // Keep this candidate-locator tokenization in sync with
    // build_static_search_index.py. A locator hit is never displayed until
    // the complete alias has been verified against the source paragraph.
    function lookupTokensForTerm(term) {
        const source = String(term || '').toLowerCase();
        const latinTokens = source.match(/[a-z0-9]+/g) || [];
        const tokens = new Set(latinTokens);
        latinTokens.filter(token => token.length >= 2).forEach(token => tokens.add(`=${token}`));
        const compactLatin = source.replace(/[\s_-]+/g, '');
        if (/^[a-z0-9]+$/.test(compactLatin) && compactLatin.length >= 2) {
            tokens.add(`=${compactLatin}`);
        }
        technicalNotationAliases(source).forEach(alias => {
            if (/^[a-z0-9.]+$/.test(alias)) {
                tokens.add(alias);
                tokens.add(`=${alias}`);
            }
        });
        const compact = source.replace(/[\s_-]+/g, '');
        const segments = compact.match(/[a-z0-9\u4e00-\u9fff]+/g) || [];
        segments.forEach(segment => {
            [2, 3].forEach(length => {
                for (let offset = 0; offset + length <= segment.length; offset += 1) {
                    tokens.add(segment.slice(offset, offset + length));
                }
            });
        });
        return [...tokens];
    }

    function bestLocatorToken(term, index) {
        return lookupTokensForTerm(term)
            .filter(token => (index.get(token) || []).length > 0)
            .sort((a, b) => (
                index.get(a).length - index.get(b).length
                || b.length - a.length
                || a.localeCompare(b)
            ))[0] || null;
    }

    function normalizeForSearchMatch(value) {
        return String(value || '').toLowerCase()
            .replace(/(^|[^a-z0-9])f\s*\/?\s*(\d+(?:\.\d+)?)(?![a-z0-9])/g, '$1f$2')
            .replace(/(^|[^a-z0-9])m\s*4\s*\/\s*3(?![a-z0-9])/g, '$1m43')
            .replace(
                /(^|[^a-z0-9])4\s*:\s*2\s*:\s*2(?![a-z0-9])/g,
                (_match, prefix) => `${prefix}422`
            )
            .replace(/[\s\-_]/g, '');
    }

    function exactSearchPattern(term) {
        const source = String(term || '').trim().toLowerCase();
        const aperture = source.match(/^f\s*\/?\s*(\d+(?:\.\d+)?)$/);
        if (aperture) return `f\\s*\\/?\\s*${escapeRegExp(aperture[1])}`;
        if (/^m\s*4\s*\/?\s*3$/.test(source)) return 'm\\s*4\\s*\\/?\\s*3';
        if (/^(?:422|4\s*:\s*2\s*:\s*2)$/.test(source)) return '(?:422|4\\s*:\\s*2\\s*:\\s*2)';
        return source.split(/[\s_-]+/).map(escapeRegExp).join('[\\s\\-_]*');
    }

    function textMatchesSearchTerm(text, term) {
        const source = String(text || '').toLowerCase();
        const candidate = String(term || '').toLowerCase();
        if (candidate === '離閃') {
            // Short spoken name for 離機閃; do not cut it out of 脫離閃燈.
            let at = source.indexOf('離閃');
            while (at >= 0) {
                if (source[at - 1] !== '脫') return true;
                at = source.indexOf('離閃', at + 2);
            }
            return false;
        }
        if (candidate === 'fc') {
            // ASR often drops the A in AF-C.  Keep the abbreviated form only
            // when the same paragraph is actually discussing focus.
            return /(^|[^a-z0-9])fc(?![a-z0-9])/i.test(source) && source.includes('對焦');
        }
        if (candidate === '觸發器') {
            // "引閃器" means a flash trigger.  A generic camera or sports
            // trigger mention alone is not evidence for that intent.
            return source.includes('觸發器')
                && ['閃燈', '閃光燈', '棚拍', '離閃', '離機閃'].some(word => source.includes(word));
        }
        if (/^[a-z0-9\s_\-/:.]+$/.test(candidate) && /[a-z0-9]/.test(candidate)) {
            // Short model names and acronyms must not match a longer token:
            // "Zf" is not "Zfc", and "GR3" is not "GR3x".  A trailing
            // number is still valid for acronyms such as "ISO800".
            const compactCandidate = normalizeForSearchMatch(candidate);
            const pattern = exactSearchPattern(candidate);
            const trailingBoundary = /\d$/.test(compactCandidate) ? '(?![a-z0-9])' : '(?![a-z])';
            return new RegExp(`(^|[^a-z0-9])${pattern}${trailingBoundary}`, 'i').test(source);
        }
        const normalizedSource = normalizeForSearchMatch(source);
        const normalizedCandidate = normalizeForSearchMatch(candidate);
        if (normalizedCandidate === '焦外') {
            // ASR sometimes repeats an inner/outer focusing or zooming term.
            // The join in 變焦外變焦 (or 面焦外面焦) is not about bokeh.
            let at = normalizedSource.indexOf('焦外');
            while (at >= 0) {
                if (normalizedSource[at - 1] !== normalizedSource[at + 2]
                    || normalizedSource[at + 3] !== '焦') {
                    return true;
                }
                at = normalizedSource.indexOf('焦外', at + 2);
            }
            return false;
        }
        return normalizedSource.includes(normalizedCandidate);
    }

    function matchingTermGroupIndexes(text, termGroups) {
        return termGroups.flatMap((group, index) => (
            group.some(term => textMatchesSearchTerm(text, term)) ? [index] : []
        ));
    }

    function labelsForIndexes(indexes, queryParts) {
        return indexes.map(index => queryParts[index]?.label).filter(Boolean);
    }

    // Highlight only aliases which literally occur in the displayed text.
    // Search matching also ignores spacing/hyphens, but inventing a highlight
    // at a non-literal location would be visually misleading.
    function literalMatchedTerms(text, termGroups, indexes) {
        const lowerText = String(text || '').toLowerCase();
        const matches = indexes.flatMap(index => termGroups[index]
            .filter(term => lowerText.includes(String(term).toLowerCase())));
        return [...new Set(matches)].sort((a, b) => b.length - a.length);
    }

    function escapeRegExp(value) {
        return String(value).replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    }

    function highlightSearchTerms(text, terms) {
        const source = String(text || '');
        const uniqueTerms = [...new Set((terms || []).filter(Boolean))]
            .sort((a, b) => String(b).length - String(a).length);
        if (!source || uniqueTerms.length === 0) return escapeHtml(source);

        const expression = new RegExp(uniqueTerms.map(escapeRegExp).join('|'), 'giu');
        let html = '';
        let offset = 0;
        for (const match of source.matchAll(expression)) {
            const start = match.index ?? 0;
            html += escapeHtml(source.slice(offset, start));
            html += `<mark class="search-highlight">${escapeHtml(match[0])}</mark>`;
            offset = start + match[0].length;
        }
        return html + escapeHtml(source.slice(offset));
    }

    function escapeHtml(value) {
        return String(value ?? '').replace(/[&<>'"]/g, character => ({
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            "'": '&#39;',
            '"': '&quot;'
        })[character]);
    }

    // These are the same deliberately narrow corrections used by the local
    // transcript audit.  They improve displayed text only: the downloadable
    // raw ASR corpus remains intact and no broad global substitution is made.
    function normalizePublicTranscript(value) {
        let text = String(value || '');
        const focalContext = /(?:\d{2,3}\s*mm|鏡頭|視角|廣角|望遠|景深)/iu.test(text);
        if (focalContext) {
            text = text.replaceAll('焦燈', '焦段').replaceAll('四角', '視角');
            if (/交代.{0,18}(?:鏡頭|廣角|望遠)|(?:鏡頭|廣角|望遠).{0,18}交代/iu.test(text)) {
                text = text.replaceAll('交代', '焦段');
            }
        }
        text = text.replace(/((?:(?:嗨|大家好|OK).{0,20}?我是)|我是)\s*(?:道子|到此|刀子|到齊)(?=[，。！？!?\s]|$)/u, '$1道慈');
        text = text.replace(/(?:道子|到此|刀子|到齊)老師/gu, '道慈老師');
        text = text.replace(/(?:在|去|做|喜歡|練習)接拍(?=的時候|時|[，。！？!?\s]|$)/gu, match => match.replace('接拍', '街拍'));
        return text;
    }

    // Keep a search card easy to scan.  The full paragraph remains the source
    // for matching and its timestamp remains clickable; this only chooses a
    // short, read-only display excerpt around the literal matched terms.
    function createSearchExcerpt(text, matchedTerms) {
        const source = String(text || '').replace(/\s+/g, ' ').trim();
        if (!source) return '';

        const terms = [...new Set((matchedTerms || [])
            .map(term => String(term || '').trim())
            .filter(Boolean))];
        const lowerSource = source.toLowerCase();
        const positions = terms
            .map(term => lowerSource.indexOf(term.toLowerCase()))
            .filter(position => position >= 0);
        const anchor = positions.length ? Math.min(...positions) : 0;
        const sentences = source.match(/[^。！？!?]+[。！？!?]?/gu) || [source];

        let cursor = 0;
        const candidate = sentences
            .map(sentence => {
                const value = sentence.trim();
                const start = source.indexOf(sentence, cursor);
                cursor = Math.max(cursor, start + sentence.length);
                const matchedCount = terms.filter(term => value.toLowerCase().includes(term.toLowerCase())).length;
                const distance = start >= 0 ? Math.abs(start - anchor) : Number.MAX_SAFE_INTEGER;
                return { value, matchedCount, distance };
            })
            .filter(item => item.value)
            .sort((a, b) => b.matchedCount - a.matchedCount || a.distance - b.distance)[0];

        const sentence = candidate?.value || source;
        // A normal sentence is the best outcome: complete, readable, and
        // directly tied to the match.  Keep a little room for spoken Chinese.
        if (sentence.length <= 52) return sentence;

        // Some ASR paragraphs lack sentence punctuation.  Do not fabricate a
        // sentence boundary: show a compact window around the match instead.
        const sentencePositions = terms
            .map(term => sentence.toLowerCase().indexOf(term.toLowerCase()))
            .filter(position => position >= 0);
        const sentenceAnchor = sentencePositions.length ? Math.min(...sentencePositions) : 0;
        const start = Math.max(0, sentenceAnchor - 12);
        const end = Math.min(sentence.length, sentenceAnchor + 32);
        const excerpt = sentence.slice(start, end).replace(/^[，、；;\s]+|[，、；;\s]+$/gu, '');
        return `${start > 0 ? '…' : ''}${excerpt}${end < sentence.length ? '…' : ''}`;
    }

    // This must match build_static_search_index.py.  FNV-1a gives a stable,
    // evenly distributed shard without revealing the entire search corpus.
    function shardIdFor(term) {
        let hash = 0x811c9dc5;
        for (let i = 0; i < term.length; i += 1) {
            hash ^= term.charCodeAt(i);
            hash = Math.imul(hash, 0x01000193);
        }
        return String((hash >>> 0) & 511).padStart(3, '0');
    }

    async function loadSearchShard(shardId) {
        if (shardCache.has(shardId)) {
            const cached = shardCache.get(shardId);
            // Map insertion order gives us a small LRU cache without keeping
            // every decompressed shard alive for the whole browser session.
            shardCache.delete(shardId);
            shardCache.set(shardId, cached);
            return cached;
        }

        const pending = (async () => {
            const response = await fetch(`/search-index/${shardId}.json.gz?v=6`, { cache: 'no-cache' });
            if (!response.ok) throw new Error(`搜尋索引分片載入失敗 (${response.status})`);
            if (!('DecompressionStream' in window)) {
                throw new Error('你的瀏覽器不支援壓縮搜尋索引');
            }
            const stream = response.body.pipeThrough(new DecompressionStream('gzip'));
            return JSON.parse(await new Response(stream).text());
        })();
        shardCache.set(shardId, pending);
        while (shardCache.size > MAX_CACHED_SHARDS) {
            shardCache.delete(shardCache.keys().next().value);
        }
        try {
            return await pending;
        } catch (error) {
            shardCache.delete(shardId);
            throw error;
        }
    }

    // Search shards contain small ASR cuts solely to locate a timestamp.  The
    // public card must instead show this independently-built paragraph context.
    // Keep the video-id hash in sync with build_public_paragraph_index.py.
    function paragraphShardIdFor(videoId) {
        let hash = 0x811c9dc5;
        for (let i = 0; i < videoId.length; i += 1) {
            hash ^= videoId.charCodeAt(i);
            hash = Math.imul(hash, 0x01000193);
        }
        return String((hash >>> 0) & 511).padStart(3, '0');
    }

    async function loadParagraphsForVideo(videoId) {
        const shardId = paragraphShardIdFor(videoId);
        if (!paragraphShardCache.has(shardId)) {
            const pending = (async () => {
                const response = await fetch(`/paragraph-index/${shardId}.json.gz`, { cache: 'no-cache' });
                if (!response.ok) throw new Error(`Paragraph index unavailable (${response.status})`);
                if (!('DecompressionStream' in window)) throw new Error('This browser cannot read the paragraph index.');
                return JSON.parse(await new Response(response.body.pipeThrough(new DecompressionStream('gzip'))).text());
            })();
            paragraphShardCache.set(shardId, pending);
            while (paragraphShardCache.size > MAX_CACHED_PARAGRAPH_SHARDS) {
                paragraphShardCache.delete(paragraphShardCache.keys().next().value);
            }
        }
        const shard = await paragraphShardCache.get(shardId);
        return shard[videoId] || [];
    }

    function paragraphAt(paragraphs, start) {
        const point = Number(start) || 0;
        // Search hits are built from the published paragraph start itself.
        // Resolve that exact source paragraph instead of accepting an
        // overlapping neighbour at the boundary (the historical "長曝"
        // false-negative happened exactly one second after the prior end).
        return paragraphs.find(item => Math.abs(Number(item.start) - point) < 0.001) || null;
    }

    async function attachParagraphContexts(results) {
        const transcriptResults = results.filter(item => !item.isTitleMatch);
        await Promise.all(transcriptResults.map(async item => {
            try {
                const paragraph = paragraphAt(await loadParagraphsForVideo(item.video_id), item.start);
                if (!paragraph) return;
                item.paragraph_id = paragraph.id;
                item.timestamp = formatTimestamp(paragraph.start);
                item.url = `https://www.youtube.com/watch?v=${item.video_id}&t=${Math.floor(paragraph.start)}s`;
                item.transcript = normalizePublicTranscript(paragraph.transcript);
                item.topic_tag = topicTag(item.transcript);
            } catch (error) {
                // A failed optional context request must not hide a search hit.
                // The UI labels this fallback as a locating excerpt, never a transcript.
                item.transcript = '';
            }
        }));
        return results;
    }

    function formatTimestamp(seconds) {
        const value = Math.max(0, Math.floor(Number(seconds) || 0));
        return `${String(Math.floor(value / 60)).padStart(2, '0')}:${String(value % 60).padStart(2, '0')}`;
    }

    function allVideosById() {
        if (videosById) return videosById;
        const videos = new Map();
        encyclopediaData.categories.forEach(category => {
            category.videos.forEach(video => videos.set(video.id, { ...video, category: category.id }));
        });
        videosById = videos;
        return videosById;
    }

    function topicTag(text) {
        const content = (text || '').toLowerCase();
        if (['光圈', 'aperture', '景深', '虛化', '散景'].some(term => content.includes(term))) return '光圈與景深';
        if (['iso', '感光度', '高感', '噪點'].some(term => content.includes(term))) return 'ISO 與感光度';
        if (['快門', 'shutter'].some(term => content.includes(term))) return '快門與動態';
        if (['對焦', '追焦', '眼對焦'].some(term => content.includes(term))) return '對焦';
        if (['鏡頭', '焦段', '35mm', '50mm', '85mm'].some(term => content.includes(term))) return '鏡頭與焦段';
        return '對話段落';
    }

    function compareSearchResultTiers(a, b) {
        return (b.matched_count || 0) - (a.matched_count || 0)
            // A timestamped spoken mention is stronger evidence than a title.
            || Number(a.isTitleMatch) - Number(b.isTitleMatch)
            || (b.specificity_score || 0) - (a.specificity_score || 0)
            || b.score - a.score;
    }

    function selectSearchResultsByTier(items, totalTerms) {
        // Reserve space for every source and match-count tier.  Otherwise a
        // broad partial title term (such as 「街拍」) can consume all 80 slots
        // before the visitor ever sees a full transcript match.
        const perTierLimit = Math.max(1, Math.floor(
            MAX_SEARCH_RESULTS / Math.max(1, totalTerms * 2)
        ));
        const selected = [];
        const selectedItems = new Set();
        const add = item => {
            if (!selectedItems.has(item) && selected.length < MAX_SEARCH_RESULTS) {
                selectedItems.add(item);
                selected.push(item);
            }
        };

        for (let matchedCount = totalTerms; matchedCount >= 1; matchedCount -= 1) {
            [false, true].forEach(isTitleMatch => {
                items
                    .filter(item => item.isTitleMatch === isTitleMatch && item.matched_count === matchedCount)
                    .sort(compareSearchResultTiers)
                    .slice(0, perTierLimit)
                    .forEach(add);
            });
        }

        // Use any spare capacity without changing the displayed hierarchy.
        items.sort(compareSearchResultTiers).forEach(add);
        return selected.sort(compareSearchResultTiers);
    }

    function searchResultVideoKey(item) {
        if (item.video_id) return item.video_id;
        const match = String(item.url || '').match(/[?&]v=([a-zA-Z0-9_-]{11})/);
        return match?.[1] || item.video_title;
    }

    function orderSearchResultsByVideo(items, termGroups) {
        const groups = new Map();

        items.forEach(item => {
            const key = searchResultVideoKey(item);
            if (!groups.has(key)) {
                groups.set(key, {
                    items: [],
                    transcriptIndexes: new Set(),
                    titleIndexes: new Set(),
                    summaryIndexes: new Set(matchingTermGroupIndexes(item.summary, termGroups)),
                    bestTranscriptCount: 0,
                    bestScore: 0,
                    clipCount: 0,
                    specificityScore: 0
                });
            }

            const group = groups.get(key);
            const matchedIndexes = item.matched_group_indexes || [];
            group.items.push(item);
            group.bestScore = Math.max(group.bestScore, item.score || 0);
            matchedIndexes.forEach(index => (
                item.isTitleMatch ? group.titleIndexes : group.transcriptIndexes
            ).add(index));
            if (!item.isTitleMatch) {
                group.bestTranscriptCount = Math.max(group.bestTranscriptCount, matchedIndexes.length);
                group.clipCount += 1;
            }
        });

        const rankedGroups = [...groups.values()];
        const groupFrequencies = Array.from({ length: termGroups.length }, () => 0);
        rankedGroups.forEach(group => {
            group.matchedIndexes = new Set([...group.transcriptIndexes, ...group.titleIndexes]);
            group.matchedIndexes.forEach(index => { groupFrequencies[index] += 1; });
        });
        rankedGroups.forEach(group => {
            group.specificityScore = [...group.matchedIndexes].reduce(
                (score, index) => score + (1 / Math.max(1, groupFrequencies[index])),
                0
            );
            group.items.forEach(item => {
                item.video_matched_count = group.matchedIndexes.size;
                item.video_total_query_terms = termGroups.length;
                item.video_match_is_complete = group.matchedIndexes.size === termGroups.length;
                item.video_transcript_matched_count = group.transcriptIndexes.size;
            });
        });

        rankedGroups.sort((a, b) => (
            b.matchedIndexes.size - a.matchedIndexes.size
            // Prefer topics spoken together over mentions scattered through
            // a long stream, or coverage supplied only by its title/summary.
            || b.bestTranscriptCount - a.bestTranscriptCount
            || b.transcriptIndexes.size - a.transcriptIndexes.size
            || b.specificityScore - a.specificityScore
            || b.summaryIndexes.size - a.summaryIndexes.size
            || b.titleIndexes.size - a.titleIndexes.size
            || b.clipCount - a.clipCount
            || b.bestScore - a.bestScore
        ));

        return rankedGroups
            .slice(0, MAX_SEARCH_RESULTS)
            .flatMap(group => group.items.sort(compareSearchResultTiers));
    }

    async function summaryRecallParagraphHits(videos, termGroups) {
        // A capped posting list can omit a video that genuinely teaches a
        // common topic. Summaries are recall hints only: every supplemental
        // hit must still be proved by the published transcript itself.
        const selected = [...videos.values()]
            .map(video => ({
                video,
                matches: matchingTermGroupIndexes(video.ai_summary, termGroups).length
            }))
            .filter(item => item.matches > 0)
            .sort((a, b) => b.matches - a.matches
                || String(b.video.publish_date || '').localeCompare(String(a.video.publish_date || ''))
                || a.video.id.localeCompare(b.video.id))
            .slice(0, MAX_SUMMARY_RECALL_VIDEOS);
        const batches = await Promise.all(selected.map(async ({ video }) => {
            try {
                const paragraphs = await loadParagraphsForVideo(video.id);
                return paragraphs.map(paragraph => ({
                    videoId: video.id,
                    start: paragraph.start,
                    matchedIndexes: matchingTermGroupIndexes(
                        normalizePublicTranscript(paragraph.transcript), termGroups
                    )
                }))
                    .filter(hit => hit.matchedIndexes.length > 0)
                    .sort((a, b) => b.matchedIndexes.length - a.matchedIndexes.length || a.start - b.start)
                    .slice(0, 2);
            } catch (error) {
                // Optional recall must not hide the normal source-backed results.
                return [];
            }
        }));
        return batches.flat();
    }

    async function staticSearch(query) {
        const queryParts = parseSearchQuery(query);
        if (queryParts.length === 0) return [];
        const termGroups = queryParts.map(part => expandTerms(part.term));
        const lookupTerms = [...new Set(termGroups.flatMap(group => group.flatMap(lookupTokensForTerm)))];
        const shards = await Promise.all([...new Set(lookupTerms.map(shardIdFor))].map(loadSearchShard));
        const index = new Map();
        shards.forEach(shard => Object.entries(shard).forEach(([term, hits]) => index.set(term, hits)));

        const videos = allVideosById();
        const scored = new Map();
        const totalTerms = termGroups.length;

        // Preserve useful partial results, but record exactly which requested
        // concepts each title contains.  A generic street-photography title
        // must say "標題符合『接拍』", never "符合『GRIII 接拍』".
        const titleCandidates = [];
        const titleGroupFrequencies = Array.from({ length: totalTerms }, () => 0);
        videos.forEach(video => {
            const title = (video.title || '').toLowerCase();
            const matchedIndexes = matchingTermGroupIndexes(title, termGroups);
            if (matchedIndexes.length > 0) {
                matchedIndexes.forEach(index => { titleGroupFrequencies[index] += 1; });
                titleCandidates.push({ video, matchedIndexes });
            }
        });
        titleCandidates.forEach(({ video, matchedIndexes }) => {
                const matchedTerms = labelsForIndexes(matchedIndexes, queryParts);
                const isCompleteMatch = matchedIndexes.length === totalTerms;
                const key = `${video.id}_title`;
                scored.set(key, {
                    score: (isCompleteMatch ? 2000000 : 100000) + (matchedIndexes.length * 10000),
                    specificity_score: matchedIndexes.reduce(
                        (score, index) => score + (1 / Math.max(1, titleGroupFrequencies[index])),
                        0
                    ),
                    video_title: video.title,
                    timestamp: '00:00',
                    text: video.title,
                    topic_tag: '📌 【標題專題討論】',
                    match_reason: `影片標題符合「${matchedTerms.join('、')}」`,
                    matched_terms: matchedTerms,
                    matched_group_indexes: matchedIndexes,
                    matched_count: matchedIndexes.length,
                    total_query_terms: totalTerms,
                    highlight_terms: literalMatchedTerms(video.title, termGroups, matchedIndexes),
                    match_is_complete: isCompleteMatch,
                    url: video.url,
                    type: '標題精確匹配',
                    isTitleMatch: true,
                    category: video.category,
                    publish_date: video.publish_date,
                    is_member_only: video.is_member_only,
                    summary: video.ai_summary || ''
                });
        });

        const addTranscriptHit = (videoId, start, groupIndexes) => {
            const timestamp = formatTimestamp(start);
            const key = `${videoId}_${timestamp}`;
            const video = videos.get(videoId);
            if (!video) return;
            let item = scored.get(key);
            if (!item) {
                item = {
                    score: 0,
                    hitGroups: new Set(),
                    video_id: videoId,
                    video_title: video.title,
                    timestamp,
                    start: Number(start) || 0,
                    locating_excerpt: '',
                    topic_tag: '對話段落',
                    match_reason: '',
                    url: `https://www.youtube.com/watch?v=${videoId}&t=${Math.floor(Number(start) || 0)}s`,
                    type: '對白同義詞檢索',
                    isTitleMatch: false,
                    category: video.category,
                    publish_date: video.publish_date,
                    is_member_only: video.is_member_only,
                    summary: video.ai_summary || ''
                };
                scored.set(key, item);
            }
            groupIndexes.forEach(groupIndex => {
                if (item.hitGroups && !item.hitGroups.has(groupIndex)) {
                    item.hitGroups.add(groupIndex);
                    item.score += 5000 * (10 ** (totalTerms - groupIndex - 1));
                }
            });
        };

        const summaryHits = await summaryRecallParagraphHits(videos, termGroups);
        summaryHits.forEach(hit => addTranscriptHit(hit.videoId, hit.start, hit.matchedIndexes));
        termGroups.forEach((group, groupIndex) => {
            group.forEach(term => {
                const locator = bestLocatorToken(term, index);
                (index.get(locator) || []).forEach(([videoId, start]) => {
                    addTranscriptHit(videoId, start, [groupIndex]);
                });
            });
        });

        const scoredCandidates = [...scored.values()]
            .map(item => {
                if (item.hitGroups) {
                    const allMatched = item.hitGroups.size === totalTerms;
                    if (allMatched) {
                        item.score += 1000000;
                    }
                    item.matched_count = item.hitGroups.size;
                    item.matched_group_indexes = [...item.hitGroups];
                    item.total_query_terms = totalTerms;
                    delete item.hitGroups;
                }
                return item;
            })
            .sort((a, b) => b.score - a.score);
        const candidates = selectSearchResultsByTier(scoredCandidates, totalTerms);
        const results = await attachParagraphContexts(candidates);
        const verifiedResults = results
            .map(item => {
                if (item.isTitleMatch) return item;

                const matchedIndexes = matchingTermGroupIndexes(item.transcript, termGroups);
                if (matchedIndexes.length === 0) return null;
                const matchedTerms = labelsForIndexes(matchedIndexes, queryParts);
                item.matched_terms = matchedTerms;
                item.matched_group_indexes = matchedIndexes;
                item.matched_count = matchedIndexes.length;
                item.total_query_terms = totalTerms;
                item.highlight_terms = literalMatchedTerms(item.transcript, termGroups, matchedIndexes);
                item.match_is_complete = matchedIndexes.length === totalTerms;
                item.match_reason = `逐字稿命中 ${matchedIndexes.length}/${totalTerms} 個搜尋詞：「${matchedTerms.join('、')}」`;
                item.transcript_excerpt = createSearchExcerpt(item.transcript, item.highlight_terms);
                return item;
            })
            .filter(Boolean);
        return orderSearchResultsByVideo(verifiedResults, termGroups);
    }

    function initTheme() {
        const savedTheme = localStorage.getItem('ppvi-theme') || 'light';
        setTheme(savedTheme);
    }

    function setTheme(theme) {
        htmlEl.setAttribute('data-theme', theme);
        localStorage.setItem('ppvi-theme', theme);

        if (themeToggleBtn) {
            const icon = themeToggleBtn.querySelector('.theme-icon');
            const text = themeToggleBtn.querySelector('.theme-text');
            if (theme === 'light') {
                if (icon) icon.textContent = '☀';
                if (text) text.textContent = '亮色模式';
            } else {
                if (icon) icon.textContent = '☾';
                if (text) text.textContent = '深色模式';
            }
        }
    }

    if (themeToggleBtn) {
        themeToggleBtn.addEventListener('click', () => {
            const currentTheme = htmlEl.getAttribute('data-theme') || 'dark';
            const nextTheme = currentTheme === 'dark' ? 'light' : 'dark';
            setTheme(nextTheme);
        });
    }

    function toggleClearBtn() {
        if (clearBtn) {
            clearBtn.style.display = searchInput.value.trim() ? 'block' : 'none';
        }
    }

    function rememberSearchLocation() {
        const url = new URL(window.location.href);
        if (lastSearchQuery) url.searchParams.set('q', lastSearchQuery);
        else url.searchParams.delete('q');
        if (currentCategory !== 'all') url.searchParams.set('category', currentCategory);
        else url.searchParams.delete('category');
        window.history.replaceState(null, '', url.pathname + url.search + url.hash);
    }

    async function showKnowledgeSuggestions(query) {
        const region = document.getElementById('knowledgeSuggestions');
        if (!region || !window.AIOKKnowledgeSearch) return;
        if (!query) {region.hidden = true; region.replaceChildren(); return;}
        try {
            knowledgePromise ||= fetch('/wiki/knowledge-lexicon.json', {cache:'no-cache'})
                .then(response => {if (!response.ok) throw new Error('knowledge index unavailable'); return response.json();});
            const lexicon = await knowledgePromise;
            if (query !== lastSearchQuery) return;
            const points = window.AIOKKnowledgeSearch.find(query, lexicon.points, 3);
            region.hidden = !points.length;
            region.innerHTML = '<span>也可以從這些知識點開始</span>' + points.map(point =>
                `<a href="${escapeHtml(point.url)}">${escapeHtml(point.display_title)} →</a>`).join('');
        } catch {region.hidden = true; knowledgePromise = null;}
    }

    if (searchInput) {
        searchInput.addEventListener('input', toggleClearBtn);
    }

    if (clearBtn) {
        clearBtn.addEventListener('click', () => {
            searchGeneration += 1;
            searchInput.value = '';
            lastSearchQuery = '';
            currentRawSearchResults = null;
            toggleClearBtn();
            renderCategory(currentCategory);
        });
    }

    if (randomBtn) {
        randomBtn.addEventListener('click', () => {
            if (!encyclopediaData || !encyclopediaData.categories) return;

            let candidateVids = [];
            if (currentCategory === 'all') {
                encyclopediaData.categories.forEach(c => {
                    if (c.videos) candidateVids.push(...c.videos);
                });
            } else {
                const catObj = encyclopediaData.categories.find(c => c.id === currentCategory);
                if (catObj && catObj.videos) {
                    candidateVids = catObj.videos;
                }
            }

            if (candidateVids.length === 0) return;

            const randomIndex = Math.floor(Math.random() * candidateVids.length);
            const selectedVid = candidateVids[randomIndex];
            const targetUrl = selectedVid.url || `https://www.youtube.com/watch?v=${selectedVid.id}&t=0s`;

            window.open(targetUrl, '_blank');
        });
    }

    function showLoadingState() {
        if (loadingOverlay) loadingOverlay.classList.add('active');
        if (searchBtn) {
            searchBtn.disabled = true;
            if (btnText) btnText.textContent = '檢索中';
        }
    }

    function hideLoadingState() {
        if (loadingOverlay) loadingOverlay.classList.remove('active');
        if (searchBtn) {
            searchBtn.disabled = false;
            if (btnText) btnText.textContent = '搜尋';
        }
    }

    async function loadEncyclopedia() {
        try {
            const res = await fetch('/catalog.json', { cache: 'no-cache' });
            if (!res.ok) throw new Error('API request failed');
            encyclopediaData = await res.json();
            videosById = null;
            const statusText = document.querySelector('[data-video-count]');
            const totalVideos = encyclopediaData?.channel_info?.total_videos;
            if (statusText && Number.isInteger(totalVideos)) {
                statusText.textContent = `${totalVideos.toLocaleString('zh-TW')} 部影片資料庫在線`;
            }
            const statusUpdated = document.querySelector('[data-updated-date]');
            const latestPublishDate = (encyclopediaData?.categories || [])
                .flatMap(category => category.videos || [])
                .map(video => video.publish_date)
                .filter(date => /^\d{4}-\d{2}-\d{2}$/.test(date || ''))
                .sort()
                .at(-1);
            if (statusUpdated && latestPublishDate) {
                statusUpdated.textContent = `更新至 ${latestPublishDate.replaceAll('-', '/')}`;
            }
            const params = new URLSearchParams(window.location.search);
            const requestedCategory = params.get('category');
            currentCategory = encyclopediaData.categories.some(c => c.id === requestedCategory) ? requestedCategory : 'all';
            document.querySelectorAll('.tab-pill').forEach(btn => btn.classList.toggle('active', btn.dataset.cat === currentCategory));
            const query = params.get('q') || '';
            searchInput.value = query;
            toggleClearBtn();
            if (query) await performSearch(query);
            else renderCategory(currentCategory);
        } catch (err) {
            console.error('Failed to load data:', err);
            resultCount.textContent = '資料載入失敗，請重新整理。';
        }
    }

    function checkIsMember(item) {
        if (typeof item.is_member_only !== 'undefined') {
            return item.is_member_only;
        }
        if (typeof item.category !== 'undefined') {
            return ['member_review', 'live', 'book'].includes(item.category);
        }
        const t = (item.title || item.video_title || "").toLowerCase();
        const kw = ["會員", "評圖", "獨家", "會後", "專屬", "限定", "直播", "週三八點半", "讀書會", "導讀"];
        return kw.some(k => t.includes(k));
    }

    function compareVideosByPublishDate(a, b) {
        const dateA = String(a?.publish_date || '');
        const dateB = String(b?.publish_date || '');
        // ISO dates sort lexicographically. Blank dates deliberately come
        // last, so unrecorded metadata never jumps ahead of new uploads.
        if (dateA !== dateB) return dateB.localeCompare(dateA);
        return String(a?.title || '').localeCompare(String(b?.title || ''));
    }

    function renderCategory(catId) {
        if (!encyclopediaData) return;
        currentCategory = catId;
        rememberSearchLocation();

        if (lastSearchQuery && currentRawSearchResults) {
            renderSearchResultsByCategory();
            return;
        }
        if (searchInterpretation) searchInterpretation.hidden = true;
        showKnowledgeSuggestions('');

        let videos = [];
        if (catId === 'all') {
            sectionTitle.textContent = '全頻道影片資料庫';
            encyclopediaData.categories.forEach(cat => {
                videos.push(...cat.videos);
            });
            
            const uniqueMap = new Map();
            videos.forEach(v => uniqueMap.set(v.id, v));
            videos = Array.from(uniqueMap.values());
        } else {
            const catObj = encyclopediaData.categories.find(c => c.id === catId);
            if (catObj) {
                sectionTitle.textContent = `${catObj.name}`;
                videos = catObj.videos;
            }
        }

        videos.sort(compareVideosByPublishDate);

        resultCount.textContent = `共 ${videos.length} 部影片`;
        renderVideoCards(videos);
        window.dispatchEvent(new Event('aiok-content-ready'));
    }

    function createVideoCardElement(v) {
        const card = document.createElement('div');
        card.className = 'video-card';
        
        const thumbUrl = `https://img.youtube.com/vi/${v.id}/hqdefault.jpg`;

        const isMember = checkIsMember(v);
        const badgeHtml = isMember 
            ? '<span class="badge-tag member-only">會員獨家</span>' 
            : '<span class="badge-tag public-free">公開影片</span>';

        const dateHtml = v.publish_date ? `<span class="card-date">發布 ${escapeHtml(v.publish_date)}</span>` : '';

        card.innerHTML = `
            <div class="thumb-container">
                <img class="card-thumb" src="${thumbUrl}" alt="${escapeHtml(v.title)}" loading="lazy">
                ${badgeHtml}
            </div>
            <div class="card-content">
                ${dateHtml ? `<div style="margin-bottom: 6px;">${dateHtml}</div>` : ''}
                <h3 class="type-lvl-3-title" title="${escapeHtml(v.title)}">${escapeHtml(v.title)}</h3>
            </div>
        `;

        card.addEventListener('click', () => {
            window.open(v.url, '_blank');
        });
        
        return card;
    }

    function renderVideoCards(videos) {
        videoGrid.innerHTML = '';
        if (videos.length === 0) {
            videoGrid.innerHTML = '<div style="grid-column: 1/-1; text-align: center; padding: 40px; color: var(--text-muted);">未找到相關影片。</div>';
            return;
        }

        const BATCH_SIZE = 24;
        let currentlyShown = 0;

        function appendNextBatch() {
            const batch = videos.slice(currentlyShown, currentlyShown + BATCH_SIZE);
            currentlyShown += batch.length;

            batch.forEach(v => {
                const card = createVideoCardElement(v);
                videoGrid.appendChild(card);
            });

            // Remove existing load more button if present
            const oldBtnContainer = document.getElementById('loadMoreContainer');
            if (oldBtnContainer) oldBtnContainer.remove();

            if (currentlyShown < videos.length) {
                const remaining = videos.length - currentlyShown;
                const loadMoreContainer = document.createElement('div');
                loadMoreContainer.id = 'loadMoreContainer';
                loadMoreContainer.style.gridColumn = '1 / -1';
                loadMoreContainer.style.textAlign = 'center';
                loadMoreContainer.style.padding = '24px 0';

                loadMoreContainer.innerHTML = `
                    <button class="search-btn" style="padding: 12px 36px; font-size: 1rem; border-radius: 16px;">
                        ▼ 載入更多影片 (還有 ${remaining} 部影片)
                    </button>
                `;

                loadMoreContainer.querySelector('button').addEventListener('click', () => {
                    appendNextBatch();
                });

                videoGrid.appendChild(loadMoreContainer);
            }
        }

        appendNextBatch();
    }

    // 🚀 使用者權威五大分類過濾器
    function filterVideoByCategory(videoTitle, clipText, catId, resultItem) {
        if (catId === 'all') return true;
        
        // 優先使用後端回傳的準確分類
        if (resultItem && resultItem.category) {
            return resultItem.category === catId;
        }
        
        // Fallback rule engine
        const text = (videoTitle + ' ' + clipText).toLowerCase();
        const isLive = ["週三八點半", "週三攝影週報", "週三攝影周報", "攝影週報", "攝影周報", "會後直播"].some(k => text.includes(k));
        const isBook = ["讀書會", "導讀", "攝影集", "畫冊", "作品集", "經典畫冊", "書報"].some(k => text.includes(k));
        const isMemberReview = text.includes("評圖") || (resultItem && resultItem.is_member_only && (text.includes("作業") || text.includes("照片")));
        const isGear = ["相機", "鏡頭", "實測", "評測", "開箱", "選購", "濾鏡", "包"].some(k => text.includes(k));

        if (catId === 'live') return isLive;
        if (catId === 'book') return isBook && !isLive;
        if (catId === 'member_review') return isMemberReview && !isLive && !isBook;
        if (catId === 'gear') return isGear && !isLive && !isBook && !isMemberReview;
        if (catId === 'daily') return !isBook && !isLive && !isMemberReview && !isGear;

        return true;
    }

    function renderSearchResultsByCategory() {
        if (!currentRawSearchResults) return;

        const groupedMap = new Map();

        currentRawSearchResults.forEach(r => {
            let vId = '';
            const match = r.url.match(/v=([a-zA-Z0-9_-]{11})/);
            if (match) vId = match[1];

            const key = vId || r.video_title;
            const clipText = r.transcript || r.locating_excerpt || '';

            if (filterVideoByCategory(r.video_title, clipText, currentCategory, r)) {
                if (!groupedMap.has(key)) {
                    groupedMap.set(key, {
                        vId: vId,
                        video_title: r.video_title,
                        publish_date: r.publish_date || '',
                        is_member_only: checkIsMember(r),
                        titleMatch: false,
                        titleMatchedTerms: [],
                        titleMatchedCount: 0,
                        totalQueryTerms: 0,
                        titleMatchIsComplete: false,
                        videoMatchedCount: r.video_matched_count || 0,
                        videoTotalQueryTerms: r.video_total_query_terms || 0,
                        videoMatchIsComplete: Boolean(r.video_match_is_complete),
                        transcriptMatchedCount: r.video_transcript_matched_count || 0,
                        videoUrl: r.isTitleMatch ? r.url : '',
                        summary: r.summary || '',
                        clips: []
                    });
                }
                const group = groupedMap.get(key);
                group.videoMatchedCount = Math.max(group.videoMatchedCount, r.video_matched_count || 0);
                group.videoTotalQueryTerms = Math.max(group.videoTotalQueryTerms, r.video_total_query_terms || 0);
                group.videoMatchIsComplete = group.videoMatchIsComplete || Boolean(r.video_match_is_complete);
                group.transcriptMatchedCount = Math.max(group.transcriptMatchedCount, r.video_transcript_matched_count || 0);
                if (!group.summary && r.summary) group.summary = r.summary;
                if (r.isTitleMatch) {
                    group.videoUrl = r.url || group.videoUrl;
                    group.titleMatch = true;
                    group.titleMatchedTerms = r.matched_terms || [];
                    group.titleMatchedCount = r.matched_count || group.titleMatchedTerms.length;
                    group.totalQueryTerms = r.total_query_terms || group.titleMatchedCount;
                    group.titleMatchIsComplete = Boolean(r.match_is_complete);
                    return;
                }
                groupedMap.get(key).clips.push({
                    timestamp: r.timestamp,
                    transcript: r.transcript || '',
                    transcript_excerpt: r.transcript_excerpt || '',
                    locating_excerpt: r.locating_excerpt || '',
                    topic_tag: r.topic_tag || '段落上下文',
                    match_reason: r.match_reason || `含關鍵字: ${lastSearchQuery}`,
                    highlight_terms: r.highlight_terms || [],
                    url: r.url
                });
            }
        });

        // The source results are already ranked as videos. Grouping here only
        // merges each video's title and timestamped evidence for display.
        const groupedVideos = Array.from(groupedMap.values());

        const catNames = {
            'all': '全頻道專題',
            'daily': '日常影片',
            'gear': '器材評測',
            'live': '直播存檔',
            'member_review': '會員評圖',
            'book': '讀書會'
        };

        const catLabel = catNames[currentCategory] || '';
        const completeCount = groupedVideos.filter(item => item.videoMatchIsComplete).length;
        const partialCount = groupedVideos.length - completeCount;
        sectionTitle.textContent = `搜尋「${lastSearchQuery}」 ‧ ${catLabel}`;
        resultCount.textContent = `共 ${groupedVideos.length} 部影片（完整 ${completeCount}、部分 ${partialCount}）`;

        videoGrid.innerHTML = '';
        if (groupedVideos.length === 0) {
            videoGrid.innerHTML = `
                <div style="grid-column: 1/-1; text-align: center; padding: 48px; color: var(--text-secondary);">
                    <div style="font-size: 1.1rem; color: var(--text-primary); font-weight: 700;">在「${escapeHtml(catLabel)}」分類中未找到「${escapeHtml(lastSearchQuery)}」相關影片</div>
                    <div style="font-size: 0.85rem; margin-top: 6px; color: var(--text-muted);">建議點選【全頻道專題】或其他分類查看完整搜尋結果</div>
                </div>`;
            return;
        }

        let activeResultTier = '';
        groupedVideos.forEach(item => {
            const resultTier = item.videoMatchIsComplete ? 'complete' : 'partial';
            if (resultTier !== activeResultTier) {
                const divider = document.createElement('div');
                divider.className = `search-tier-divider ${resultTier}`;
                divider.innerHTML = resultTier === 'complete'
                    ? '<strong>完整符合</strong><span>同一支影片的標題或逐字稿涵蓋全部搜尋詞</span>'
                    : '<strong>部分相關</strong><span>只符合部分搜尋詞，供延伸查找</span>';
                videoGrid.appendChild(divider);
                activeResultTier = resultTier;
            }

            const card = document.createElement('div');
            card.className = 'video-card';

            const thumbUrl = item.vId ? `https://img.youtube.com/vi/${item.vId}/hqdefault.jpg` : '';
            const badgeHtml = item.is_member_only 
                ? '<span class="badge-tag member-only">會員獨家</span>' 
                : '<span class="badge-tag public-free">公開影片</span>';

            let featureBadgeHtml = '';
            if (item.clips.length >= 3) {
                featureBadgeHtml = `<span class="featured-label">「${escapeHtml(lastSearchQuery)}」主題精華</span>`;
            }

            const dateHtml = item.publish_date ? `<span class="card-date">發布 ${escapeHtml(item.publish_date)}</span>` : '';

            const INITIAL_SHOW = 2;
            const visibleClips = item.clips.slice(0, INITIAL_SHOW);
            const hiddenClips = item.clips.slice(INITIAL_SHOW);

            const titleMatchedTerms = item.titleMatchedTerms.length
                ? item.titleMatchedTerms.join('、')
                : lastSearchQuery;
            const titleMatchDescription = `標題命中 ${item.titleMatchedCount}/${item.totalQueryTerms} 個搜尋詞：「${titleMatchedTerms}」`;
            const summaryHtml = item.summary
                ? `<div class="summary-block"><div class="summary-label">影片摘要</div><div class="summary-text">${escapeHtml(item.summary)}</div></div>`
                : '';
            let clipsHtml = '<div class="clips-wrapper">';
            // Title and transcript are distinct evidence sources.  Keep the
            // title tier visible even when the video also has transcript hits.
            if (item.titleMatch) {
                clipsHtml += `
                    <div class="clip-node title-match-node">
                        <div class="match-reason-pill">${escapeHtml(titleMatchDescription)}</div>
                        ${item.clips.length === 0
                            ? `<div class="quote-text">${item.titleMatchIsComplete ? '標題包含所有搜尋詞' : '標題只符合部分搜尋詞'}；目前尚未找到可定位的逐字稿時間點，點卡片可從影片開頭觀看。</div>`
                            : ''}
                    </div>
                `;
            }
            
            visibleClips.forEach(clip => {
                clipsHtml += `
                    <div class="clip-node" data-url="${escapeHtml(clip.url)}">
                        <div class="clip-meta">
                            <span class="topic-label">${escapeHtml(clip.topic_tag)}</span>
                            <span class="ts-link">${clip.timestamp}</span>
                        </div>
                        <div class="match-reason-pill">${escapeHtml(clip.match_reason)}</div>
                        <div class="quote-text">${clip.transcript ? `逐字稿：${highlightSearchTerms(clip.transcript_excerpt || clip.transcript, clip.highlight_terms)}` : `命中片段（完整段落載入失敗）：${escapeHtml(createSearchExcerpt(clip.locating_excerpt, clip.highlight_terms))}`}</div>
                    </div>
                `;
            });

            if (hiddenClips.length > 0) {
                clipsHtml += `<div class="more-clips-container" style="display: none;">`;
                hiddenClips.forEach(clip => {
                    clipsHtml += `
                        <div class="clip-node" data-url="${escapeHtml(clip.url)}">
                            <div class="clip-meta">
                                <span class="topic-label">${escapeHtml(clip.topic_tag)}</span>
                            <span class="ts-link">${clip.timestamp}</span>
                            </div>
                            <div class="match-reason-pill">${escapeHtml(clip.match_reason)}</div>
                            <div class="quote-text">${clip.transcript ? `逐字稿：${highlightSearchTerms(clip.transcript_excerpt || clip.transcript, clip.highlight_terms)}` : `命中片段（完整段落載入失敗）：${escapeHtml(createSearchExcerpt(clip.locating_excerpt, clip.highlight_terms))}`}</div>
                        </div>
                    `;
                });
                clipsHtml += `</div>`;
                clipsHtml += `
                    <button class="fold-btn">
                        <span>▼ 展開更多 ${hiddenClips.length} 個對話片段</span>
                    </button>
                `;
            }

            clipsHtml += '</div>';

            card.innerHTML = `
                <div class="thumb-container">
                    <img class="card-thumb" src="${thumbUrl}" alt="${escapeHtml(item.video_title)}" loading="lazy">
                    ${badgeHtml}
                    <span class="ts-badge">${item.clips.length ? `${item.clips.length} 個可定位片段` : '標題符合'}</span>
                </div>
                <div class="card-content">
                    ${dateHtml ? `<div style="margin-bottom: 6px;">${dateHtml}</div>` : ''}
                    ${featureBadgeHtml}
                    <h3 class="type-lvl-3-title">${escapeHtml(item.video_title)}</h3>
                    ${summaryHtml}
                    ${clipsHtml}
                </div>
            `;

            const expandBtn = card.querySelector('.fold-btn');
            if (expandBtn) {
                expandBtn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    const moreContainer = card.querySelector('.more-clips-container');
                    if (moreContainer.style.display === 'none') {
                        moreContainer.style.display = 'flex';
                        moreContainer.style.flexDirection = 'column';
                        moreContainer.style.gap = '14px';
                        moreContainer.style.marginTop = '14px';
                        expandBtn.innerHTML = '<span>▲ 收起對話片段</span>';
                    } else {
                        moreContainer.style.display = 'none';
                        expandBtn.innerHTML = `<span>▼ 展開更多 ${hiddenClips.length} 個對話片段</span>`;
                    }
                });
            }

            card.querySelectorAll('.clip-node').forEach(clipEl => {
                clipEl.addEventListener('click', (e) => {
                    e.stopPropagation();
                    const targetUrl = clipEl.dataset.url;
                    window.open(targetUrl, '_blank');
                });
            });

            card.addEventListener('click', (e) => {
                if (!e.target.closest('.fold-btn')) {
                    if (item.clips.length > 0) {
                        window.open(item.clips[0].url, '_blank');
                    } else if (item.videoUrl) {
                        window.open(item.videoUrl, '_blank');
                    }
                }
            });

            videoGrid.appendChild(card);
        });
    }

    async function performSearch(query) {
        const cleanQuery = query.trim();
        const topics = parseNaturalSearchQuery(cleanQuery);
        if (searchInterpretation) {
            searchInterpretation.hidden = !topics;
            searchInterpretation.textContent = topics
                ? `搜尋主題：${topics.map(part => part.label).join('、')}。完整符合表示主題都有出現，可點時間查看原片說明。`
                : '';
        }
        if (!cleanQuery) {
            searchGeneration += 1;
            lastSearchQuery = '';
            currentRawSearchResults = null;
            renderCategory(currentCategory);
            return;
        }

        if (isSearching) return;
        isSearching = true;
        const generation = ++searchGeneration;

        showLoadingState();

        lastSearchQuery = cleanQuery;
        rememberSearchLocation();
        showKnowledgeSuggestions(cleanQuery);
        sectionTitle.textContent = `搜尋「${cleanQuery}」觀點與時間軸`;
        resultCount.textContent = '正在搜尋索引...';

        try {
            const results = await staticSearch(cleanQuery);
            if (generation !== searchGeneration) return;
            currentRawSearchResults = results;
            renderSearchResultsByCategory();
        } catch (err) {
            console.error('Search failed:', err);
            resultCount.textContent = '搜尋發生錯誤。';
        } finally {
            hideLoadingState();
            isSearching = false;
            window.dispatchEvent(new Event('aiok-content-ready'));
        }
    }

    categoryTabs.addEventListener('click', (e) => {
        if (e.target.classList.contains('tab-pill')) {
            document.querySelectorAll('.tab-pill').forEach(btn => btn.classList.remove('active'));
            e.target.classList.add('active');
            const catId = e.target.dataset.cat;
            currentCategory = catId;
            renderCategory(catId);
        }
    });

    searchBtn.addEventListener('click', () => {
        performSearch(searchInput.value);
    });

    searchInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            performSearch(searchInput.value);
        }
    });

    hotTags.forEach(tag => {
        tag.addEventListener('click', () => {
            const keyword = tag.dataset.tag;
            searchInput.value = keyword;
            toggleClearBtn();
            performSearch(keyword);
        });
    });

    initTheme();
    loadEncyclopedia();
});
