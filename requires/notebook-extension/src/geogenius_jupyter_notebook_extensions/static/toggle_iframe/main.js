// Adapted from https://gist.github.com/magican/5574556
// by minrk https://github.com/minrk/ipython_extensions
// See the history of contributions in README.md

define([
    'require',
    'jquery',
    'base/js/namespace',
    'base/js/events',
    'notebook/js/codecell',
    'nbextensions/toggle_iframe/toc2',
    'nbextensions/toggle_iframe/config'
], function (
    requirejs,
    $,
    Jupyter,
    events,
    codecell,
    toc2,
    iframeConfig
) {
    "use strict";

    // imports
    var table_of_contents = toc2.table_of_contents;
    var toggle_panel = toc2.toggle_panel;
    var IPython = Jupyter;

    var add_button_to_tollbar = function (cfg) {
        if (!IPython.toolbar) {
            events.on("app_initialized.NotebookApp", function (evt) {
                add_button_to_tollbar(cfg);
            });
            return;
        }
        if ($("#toc_button").length === 0) {
            $(IPython.toolbar.add_buttons_group([
                Jupyter.keyboard_manager.actions.register({
                    'help': 'Table of Contents',
                    'icon': 'fa-list',
                    'handler': function () {
                        toggle_panel(cfg);
                    },
                }, 'toggle-data-panel', 'data-list')
            ])).find('.btn').attr('id', 'toc_button');
        }
    };

    var load_css = function () {
        var link = document.createElement("link");
        link.type = "text/css";
        link.rel = "stylesheet";
        link.href = requirejs.toUrl("./main.css");
        document.getElementsByTagName("head")[0].appendChild(link);
    };

    function create_additional_css(cfg) {
        var sheet = document.createElement('style');
        if (cfg.moveMenuLeft) {
            sheet.innerHTML += "div#menubar-container, div#header-container {\n" +
                "width: auto;\n" +
                "padding-left: 20px; }"
        }
        // Using custom colors
        sheet.innerHTML += "#toc-wrapper { background-color: " + cfg.colors.wrapper_background + "}\n";
        sheet.innerHTML += "#toc a, #navigate_menu a, .toc { color: " + cfg.colors.navigate_text + "}";   //导航栏图标颜色
        sheet.innerHTML += "#toc-wrapper .toc-item-num { color: " + cfg.colors.navigate_num + "}";
        sheet.innerHTML += ".sidebar-wrapper { border-color: " + cfg.colors.sidebar_border + "}";
        document.body.appendChild(sheet);
    }

    function update_params(params) {
        $.extend(params, iframeConfig);
        var config = Jupyter.notebook.config;
        for (var key in params) {
            if (config.data.hasOwnProperty(key))
                params[key] = config.data[key];
        }
        params.locUrl = window.location.href;
        return params
    }


    var toc_init = function () {
        // read configuration, then call toc
        IPython.notebook.config.loaded.then(function () {
            var cfg = toc2.read_config();
            cfg = update_params(cfg);
            // create highlights style section in document
            create_additional_css(cfg);
            // add toc toggle button (now that cfg has loaded)
            add_button_to_tollbar(cfg);
            // call main function with newly loaded config
            table_of_contents(cfg);
            toc2.receiveMessageInit(cfg)
        });
    };

    var load_ipython_extension = function () {
        load_css(); //console.log("Loading css")

        // Wait for the notebook to be fully loaded
        if (Jupyter.notebook !== undefined && Jupyter.notebook._fully_loaded) {
            // this tests if the notebook is fully loaded
            console.log("Notebook fully loaded -- extension initialized ");
            toc_init();
        } else {
            console.log("extension waiting for notebook availability");
            events.on("notebook_loaded.Notebook", function () {
                console.log("extension initialized (via notebook_loaded)");
                toc_init();
            })
        }
    };

    return {
        load_ipython_extension: load_ipython_extension,
    };
});
