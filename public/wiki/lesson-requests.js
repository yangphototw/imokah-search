// A successful UI state requires an acknowledged server response.
(function (root) {
    const config = root.AIOK_REQUEST_CONFIG || {};
    const endpoint = config.endpoint;
    let inFlight = false;
    function visitorId() {
        const key = 'aiok-request-visitor';
        let id = localStorage.getItem(key);
        if (!/^[a-f0-9-]{36}$/i.test(id || '')) {
            id = crypto.randomUUID();
            localStorage.setItem(key, id);
        }
        return id;
    }
    async function call(body) {
        const controller = new AbortController();
        const timer = setTimeout(() => controller.abort(), 15000);
        try {
            const response = await fetch(endpoint, {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(body), signal:controller.signal});
            if (!response.ok) throw new Error('service unavailable');
            const payload = await response.json();
            if (!payload.ok) throw new Error('request rejected');
            return payload;
        } finally {clearTimeout(timer);}
    }
    async function vote(topicId) {
        if (!endpoint) return {status:'preview'};
        if (inFlight) return {status:'busy'};
        inFlight = true;
        try {
            const result = await call({action:'vote',topicId,visitorId:visitorId()});
            if (result.topicId !== topicId || !Number.isInteger(result.count) || result.count < 1) throw new Error('invalid receipt');
            return {status:'received',count:result.count,duplicate:result.duplicate === true};
        } catch { return {status:'failed'}; }
        finally {inFlight=false;}
    }
    async function counts() {
        if (!endpoint) return null;
        const result = await call({action:'counts'});
        if (!result.counts || Object.values(result.counts).some(n => !Number.isInteger(n) || n < 0)) throw new Error('invalid counts');
        return result.counts;
    }
    root.AIOKLessonRequests = {vote, counts, enabled:!!endpoint};
})(window);
