
//
// Pretty print data.
//
function PP(data) {
    return JSON.stringify(data);
}

//
// Format an int with spaces.
//
export let format_int = function(int) {
    var str = "" + int;
    var res = "";
    for (var i = 0; i < str.length; i+=3) {
        res = str.substring(str.length - i - 3, str.length - i) + " " + res;
    }
    return $.trim(res);
};


//
// Deferred resolved when document is ready.
//
export let deferred_doc_ready = () => {
    var deferred = $.Deferred();
    $(() => deferred.resolve());
    return deferred;
};


//
// Get value from fragment identifier.
//
export let get_hash = function(key) {
    var vars = window.location.hash.substring(1).split("&");
    for (var i = 0; i < vars.length; ++i) {
        var pair = vars[i].split('=');
        if (pair[0] == key) {
            return pair[1];
        }
    }
};

//
// Set value in fragment identifier.
//
export let set_hash = function(key, value) {
    var vars = window.location.hash.substring(1).split("&").filter(function(x) { return x !== ''; });
    var item = key + '=' + value;
    for (var i = 0; i < vars.length; ++i) {
        var pair = vars[i].split('=');
        if (pair[0] == key) {
            vars[i] = item;
            item = undefined;
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
    var value;
    if (document.cookie && document.cookie !== '') {
        var cookies = document.cookie.split(';');
        for (var i = 0; i < cookies.length; i++) {
            var cookie = jQuery.trim(cookies[i]);
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                value = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return value;
};

