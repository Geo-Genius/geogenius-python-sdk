(requirejs.specified('base/js/namespace') ? define : function (deps, callback) {
    "use strict";
    // if here, the Jupyter namespace hasn't been specified to be loaded.
    // This means that we're probably embedded in a page, so we need to make
    // our definition with a specific module name
    return define('nbextensions/toggle_iframe/config', deps, callback);
})(function () {
    return {
        //local developer should update this to local frontend
        // if user forget set_config,then we will use this url
        side_data_searcher_iframe_src: "http://100.94.14.213:8080/extensions/notebook",
        geogenius_pacakge_import_catalogImage:'from geogeniustools.images.catalog_image import CatalogImage'
    }
});