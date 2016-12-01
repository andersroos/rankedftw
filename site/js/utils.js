
//
// Deferred resolved when document is ready.
//
export let deferred_doc_ready = () => {
    var deferred = $.Deferred();
    $(() => deferred.resolve());
    return deferred;
};

