// TODO Do some serious testing in all the browsers.

//
// Format an int with spaces.
//
export let format_int = function(int) {
    let str = "" + int;
    let res = "";
    for (let i = 0; i < str.length; i+=3) {
        res = str.substring(str.length - i - 3, str.length - i) + " " + res;
    }
    return res.trim();
};

//
// Return a promise of body parsed as json, non 200 or failed parsing body as json is reject.
//
export const fetch_json = url => fetch(url)
    .then(response => {
        if (!response.ok) throw new Error(`failed to fetch from ${url}: ${response}`);
        return response.json();
    })

//
// Returns a promise for when the document is ready.
//
export const doc_ready = () => new Promise(resolve => {
    if (document.readyState === "complete") {
        resolve();
    }
    else {
        document.addEventListener("DOMContentLoaded", resolve);
    }
});


//
// Get value from fragment identifier.
//
export let get_hash = function(key) {
    const vars = window.location.hash.substring(1).split("&");
    for (let i = 0; i < vars.length; ++i) {
        const pair = vars[i].split('=');
        if (pair[0] === key) {
            return pair[1];
        }
    }
    return null;
};

//
// Set value in fragment identifier.
//
export let set_hash = function(key, value) {
    const vars = window.location.hash.substring(1).split("&").filter(function(x) { return x !== ''; });
    let item = key + '=' + value;
    for (let i = 0; i < vars.length; ++i) {
        const pair = vars[i].split('=');
        if (pair[0] === key) {
            vars[i] = item;
            item = null;
            break;
        }
    }
    if (item) {
        vars.push(item);
    }
    window.history.replaceState('', '', '#' + vars.join('&'));
};

//
// Set cookie.
//
export let set_cookie = function(name, value, path, expiry) {
    path = path || "/";
    expiry = expiry || "1 Jan 2100 01:01:01 GMT";
    document.cookie = name + "=" + value + ";expires=" + expiry + ";path=" + path;
};

//
// Get cookie.
//
export let get_cookie = function(name) {
    let value;
    if (document.cookie && document.cookie !== '') {
        let cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            let cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                value = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return value;
};

//
// Return the value value, but make sure it is in the range [min, max].
//
export let min_max = function(min, value, max) {
    return Math.min(Math.max(min, value), max);
};

//
// Like each but reverse.
//
export let rev_each = function(list, fun) {
    for (let i = list.length - 1; i >= 0; --i) {
        fun(list[i], i);
    }
};

