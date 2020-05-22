(requirejs.specified('base/js/namespace') ? define : function (deps, callback) {
    "use strict";
    // if here, the Jupyter namespace hasn't been specified to be loaded.
    // This means that we're probably embedded in a page, so we need to make
    // our definition with a specific module name
    return define('nbextensions/toggle_iframe/toc2', deps, callback);
})(['jquery', 'require'], function ($, requirejs) {
    "use strict";

    //global args
    var IPython;
    var events;
    var liveNotebook = false;

    // default values for system-wide configurable parameters
    var default_cfg = {
        colors: {
            wrapper_background: '#FFFFFF',
            sidebar_border: '#EEEEEE',
            navigate_text: '#333333',
            navigate_num: '#000000',
            on_scroll: '#2447f0',
        },
        collapse_to_match_collapsible_headings: false,
        markTocItemOnScroll: true,
        moveMenuLeft: true,
        navigate_menu: true,
        threshold: 4,
        widenNotebook: false,
        locUrl: ''
    };
    // default values for per-notebook configurable parameters
    var metadata_settings = {
        sideBar: true,              //是否挂靠在边上
        base_numbering: 1,
        toc_position: {},
        toc_section_display: true,
        toc_window_display: false,
    };
    $.extend(true, default_cfg, metadata_settings);

    /**
     * try to get bootstrap tooltip plugin.
     * The require call may fail, since the plugin doesn't seem to be included
     * in all Jupyter versions. In this case, we fallback to using jqueryui tooltips.
     */
    var have_bs_tooltips = false;
    requirejs(
        ['components/bootstrap/js/tooltip'],
        // we don't actually need to do anything with the return
        // just ensure that the plugin gets loaded.
        function () {
            have_bs_tooltips = true;
        },
        // The errback, error callback
        // The error has a list of modules that failed
        function (err) {
            var failedId = err.requireModules && err.requireModules[0];
            if (failedId === 'components/bootstrap/js/tooltip') {
                // could do something here, like load a cdn version.
                // For now, just ignore it.
                have_bs_tooltips = false;
            }
        }
    );

    /**
     * init receive message from geogenius origin
     */
    var receiveMessageInit = function (cfg) {
        var handleMessage = function (e) {
            try {
                var iframe_url = new URL(cfg.side_data_searcher_iframe_src);
                if (e.origin === iframe_url.origin) {
                    let data = e.data;
                    //1.检查是否需要导入catalogImages
                    let isImport = checkImport();
                    if (!isImport) {
                        //1.1导入geogenius包，执行
                        let importIndex = findFirstCodeCell();
                        createCellAndRun(importIndex, cfg.geogenius_pacakge_import_catalogImage, true, false);
                    }
                    //2.底部插入执行data
                    let cells_len = Jupyter.notebook.ncells();
                    Jupyter.notebook.select(cells_len - 1);
                    let last_cell = Jupyter.notebook.get_selected_cell();
                    if (!last_cell.get_text()) {
                        //2.1最后一个内容如果为空，原地插入执行
                        last_cell.set_text(data);
                        last_cell.execute()
                    } else {
                        //2.2不为空，创建插入
                        let lastIndex = Math.max(Jupyter.notebook.get_selected_index(), Jupyter.notebook.get_anchor_index()) + 1;
                        createCellAndRun(lastIndex, data, true);
                        Jupyter.notebook.select(lastIndex);
                        Jupyter.notebook.scroll_to_bottom();
                    }
                } else {
                    throw "untrusted origin send a message";
                }
            } catch (e) {
                console.error(e)
            }
        };

        if (typeof window.addEventListener != 'undefined') {
            window.addEventListener('message', handleMessage, false);
        } else if (typeof window.attachEvent != 'undefined') {
            window.attachEvent('onmessage', handleMessage);
        }
    };

    var checkImport = function () {
        let cells = Jupyter.notebook.get_cells();
        let cells_len = cells.length;
        for (let i = 0; i < cells_len; i++) {
            let cell = cells[i];
            if (cell.cell_type === "code") {
                let content = cell.get_text();
                if (content && content.indexOf("geogeniustools.images.catalog_image") !== -1 && content.indexOf("CatalogImage") !== -1) {
                    return true
                }
            }
        }
        return false
    };

    /**
     * get the index of the first codecell
     * @returns {number}
     */
    var findFirstCodeCell = function () {
        let cells = Jupyter.notebook.get_cells();
        let cells_len = cells.length;
        let index = 0;
        for (let i = 0; i < cells_len; i++) {
            let cell = cells[i];
            if (cell.cell_type === "code") {
                index = i;
                break
            }
        }
        return index
    };

    /**
     *  create a cell ,insert content, if nedd run run it
     * @param  {integer} [index ]- the position you want insert a cell
     * @param  {string} [content] -
     * @param  {boolean} [execute] -
     * @param  {boolean} [select] -
     * @return {Cell} created cell
     */
    var createCellAndRun = function (index, content, execute, select) {
        execute = (execute === undefined) ? false : execute;
        select = (select === undefined) ? false : select;

        let cell = Jupyter.notebook.insert_cell_at_index("code", index);
        cell.set_text(content);
        if (execute) {
            cell.execute();
        }
        if (select) {
            cell.select()
        }
        return cell
    };

    /**
     *  Read our config from server config & notebook metadata
     *  This function should only be called when both:
     *   1. the notebook (and its metadata) has fully loaded
     *   2. Jupyter.notebook.config.loaded has resolved
     */
    var read_config = function () {
        var cfg = default_cfg;
        cfg.locUrl = window.location.href;
        if (!liveNotebook) {
            return cfg;
        }
        // config may be specified at system level or at document level.
        // first, update defaults with config loaded from server
        $.extend(true, cfg, IPython.notebook.config.data.toc2);
        // ensure notebook metadata has toc object, cache old values
        var md = IPython.notebook.metadata.toc || {};
        // reset notebook metadata to remove old values
        IPython.notebook.metadata.toc = {};
        // then update cfg with any found in current notebook metadata
        // and save in nb metadata (then can be modified per document)
        Object.keys(metadata_settings).forEach(function (key) {
            cfg[key] = IPython.notebook.metadata.toc[key] = (md.hasOwnProperty(key) ? md : cfg)[key];
        });
        return cfg;
    };

    // globally-used status variables:
    // toc_position default also serves as the defaults for a non-live notebook
    var toc_position = {height: 'calc(100% - 180px)', width: '20%', left: '10px', top: '150px'};

    try {
        // this will work in a live notebook because nbextensions & custom.js
        // are loaded by/after notebook.js, which requires base/js/namespace
        IPython = requirejs('base/js/namespace');
        events = requirejs('base/js/events');
        liveNotebook = true;
    } catch (err) {
        // We *are* theoretically in a non-live notebook
        console.log('extension working in non-live notebook');
        // in non-live notebook, there's no event structure, so we make our own
        if (window.events === undefined) {
            var Events = function () {
            };
            window.events = $([new Events()]);
        }
        events = window.events;
    }

    var Jupyter = IPython;

    var setMd = function (key, value) {
        if (liveNotebook) {
            var md = IPython.notebook.metadata.toc;
            if (md === undefined) {
                md = IPython.notebook.metadata.toc = {};
            }
            var old_val = md[key];
            md[key] = value;
            if (typeof _ !== undefined ? !_.isEqual(value, old_val) : old_val != value) {
                IPython.notebook.set_dirty();
            }
        }
        return value;
    };

    function setNotebookWidth(cfg, st) {
        var margin = 20;
        var nb_inner = $('#notebook-container');
        var nb_wrap_w = $('#notebook').width();
        var sidebar = $('#toc-wrapper');
        var visible_sidebar = cfg.sideBar && sidebar.is(':visible');
        var sidebar_w = visible_sidebar ? sidebar.outerWidth() : 0;
        var available_space = nb_wrap_w - 2 * margin - sidebar_w;
        var inner_css = {marginLeft: '', width: ''};
        if (cfg.widenNotebook) {
            inner_css.width = available_space;
        }
        if (visible_sidebar) {
            var nb_inner_w = nb_inner.outerWidth();
            if (available_space <= nb_inner_w + sidebar_w) {
                inner_css.marginLeft = sidebar_w + margin; // shift notebook rightward to fit the sidebar in
                if (available_space <= nb_inner_w) {
                    inner_css.width = available_space; // also slim notebook to fit sidebar
                }
            }
        }
        nb_inner.css(inner_css);
    }

    var saveTocPosition = function () {
        var toc_wrapper = $('#toc-wrapper');
        var new_values = toc_wrapper.hasClass('sidebar-wrapper') ? ['width'] : ['left', 'top', 'height', 'width'];
        $.extend(toc_position, toc_wrapper.css(new_values));
        setMd('toc_position', toc_position);
    };
    //缩小内容区域
    var makeUnmakeMinimized = function (cfg, animate) {
        var open = cfg.sideBar || cfg.toc_section_display;
        var new_css, wrap = $('#toc-wrapper');
        var anim_opts = {duration: animate ? 'fast' : 0};
        if (open) {
            $('#side_data_iframe').show();
            new_css = cfg.sideBar ? {} : {height: toc_position.height, width: toc_position.width};
        } else {
            new_css = {
                height: wrap.outerHeight() - wrap.find('#toc').outerHeight(),
            };
            anim_opts.complete = function () {
                $('#side_data_iframe').hide();
                $('#toc-wrapper').css('width', '');
            };
        }
        wrap.toggleClass('closed', !open)
            .animate(new_css, anim_opts)
            .find('.hide-btn').attr('title', open ? 'Hide ToC' : 'Show ToC');
        return open;
    };

    //放大到全屏或者缩小到原来位置
    var switchWrapper = function (open, cfg, animate) {
        var new_css, wrap = $('#toc-wrapper');
        var view_rect = (liveNotebook ? document.getElementById('site') : document.body).getBoundingClientRect();
        var anim_opts = {duration: animate ? 'fast' : 0};
        if (open) {
            new_css = {height: view_rect.height, width: view_rect.width, left: 0, top: view_rect.top};
        } else {
            new_css = {height: view_rect.height, width: "480px", left: 0, top: view_rect.top};
            $.extend(toc_position, new_css);
            anim_opts.complete = function () {
                setNotebookWidth(cfg);
                $('#toc-wrapper').css('width', "480px");
            };
        }
        wrap.toggleClass('closed', !open)
            .animate(new_css, anim_opts)
            .find('.hide-btn').attr('title', open ? 'Hide' : 'Show');
    };

    //控制sidebar边界并刷新notebook边界
    var makeUnmakeSidebar = function (cfg) {
        var make_sidebar = cfg.sideBar;
        //获取site元素边界
        var view_rect = (liveNotebook ? document.getElementById('site') : document.body).getBoundingClientRect();
        var wrap = $('#toc-wrapper')
            .toggleClass('sidebar-wrapper', make_sidebar)
            .toggleClass('float-wrapper', !make_sidebar)
            .resizable('option', 'handles', make_sidebar ? 'e' : 'all');
        wrap.children('.ui-resizable-se').toggleClass('ui-icon', !make_sidebar);
        wrap.children('.ui-resizable-e').toggleClass('ui-icon ui-icon-grip-dotted-vertical', make_sidebar);
        if (make_sidebar) {
            wrap.css({top: view_rect.top, height: '', left: 0});
        } else {
            wrap.css({height: toc_position.height});
        }
        setNotebookWidth(cfg);
    };

    var build_side_panel = function (cfg, st) {
        var callbackPageResize = function (evt) {
            setNotebookWidth(cfg);
        };
        var side_panel_expand_contract = $('<i class="fa fa-right fa-expand hidden-print">');

        var toc_wrapper = $('<div id="toc-wrapper"/>')
            .css('display', 'none')
            .append(
                $('<div id="panel-header"/>')
                    .append(
                        $('<i class="fa fa-fw hide-btn" title="Hide ToC">')
                            .on('click', function (evt) {
                                cfg.toc_section_display = setMd('toc_section_display', !cfg.toc_section_display);
                                makeUnmakeMinimized(cfg, true);
                            })
                    ).append(
                    $('<i class="fa fa-fw fa-refresh" title="Reload">')
                        .on('click', function (evt) {
                            var icon = $(evt.currentTarget).addClass('fa-spin');
                            table_of_contents(cfg, st);
                            icon.removeClass('fa-spin');
                        })
                ).append(
                    $('<i class="fa fa-fw fa-cog" title="settings"/>')
                        .on('click', function (evt) {
                            show_settings_dialog(cfg, st);
                        })
                ).append(side_panel_expand_contract)
            ).append(
                $("<iframe src='" + cfg.side_data_searcher_iframe_src + "?parentLocation=" + cfg.locUrl + "'  id='side_data_iframe'></iframe>")
            ).append(
                $("<div id='iframe_mask'></div>")
            )
            .prependTo(liveNotebook ? '#site' : document.body);

        side_panel_expand_contract.attr({
            title: 'expand/contract panel',
            'data-toggle': 'tooltip'
        }).tooltip({
            placement: 'right'
        }).click(function () {
            var open = $(this).hasClass('fa-expand');
            $(this).toggleClass('fa-expand', !open).toggleClass('fa-compress', open);

            switchWrapper(open, cfg, true)

            var tooltip_text = (open ? 'shrink to not' : 'expand to') + ' fill the window';
            if (have_bs_tooltips) {
                side_panel_expand_contract.attr('title', tooltip_text);
                side_panel_expand_contract.tooltip('hide').tooltip('fixTitle');
            } else {
                side_panel_expand_contract.tooltip('option', 'content', tooltip_text);
            }
        });

        // enable dragging and save position on stop moving
        toc_wrapper.draggable({
            drag: function (event, ui) {
                var make_sidebar = ui.position.left < 20; // 20 is snapTolerance
                if (make_sidebar) {
                    ui.position.top = (liveNotebook ? document.getElementById('site') : document.body).getBoundingClientRect().top;
                    ui.position.left = 0;
                }
                if (make_sidebar !== cfg.sideBar) {
                    cfg.toc_section_display = setMd('toc_section_display', true);
                    cfg.sideBar = setMd('sideBar', make_sidebar);
                    makeUnmakeMinimized(cfg);
                    makeUnmakeSidebar(cfg);
                }
            }, //end of drag function
            stop: saveTocPosition,
            containment: 'parent',
            snap: 'body, #site',
            snapTolerance: 20,
        });

        toc_wrapper.resizable({
            handles: 'all',
            resize: function (event, ui) {
                if (cfg.sideBar) {
                    $('#toc-wrapper').css('height', '');
                    // unset the height set by jquery resizable
                    setNotebookWidth(cfg, st)
                }
            },
            start: function (event, ui) {
                $("#iframe_mask").css("z-index", "999");
                if (!cfg.sideBar) {
                    cfg.toc_section_display = setMd('toc_section_display', true);
                    makeUnmakeMinimized(cfg);
                }
            },
            stop: function () {
                $("#iframe_mask").css("z-index", "0");
                saveTocPosition()
            },
            containment: 'parent',
            minHeight: 100,
            minWidth: 165
        });

        // On header/toolbar resize, resize the toc itself
        $(window).on('resize', callbackPageResize);
        if (liveNotebook) {
            events.on("resize-header.Page toggle-all-headers", callbackPageResize);
            $.extend(toc_position, IPython.notebook.metadata.toc.toc_position);
        } else {
            // default to true for non-live notebook
            cfg.toc_window_display = true;
        }
        // restore toc position at load
        toc_wrapper.css(cfg.sideBar ? {width: toc_position.width} : toc_position);
        // older toc2 versions stored string representations, so update those
        if (cfg.toc_window_display === 'none') {
            cfg.toc_window_display = setMd('toc_window_display', false);
        }
        if (cfg.toc_section_display === 'none') {
            cfg.toc_section_display = setMd('toc_section_display', false);
        }
        toc_wrapper.toggle(cfg.toc_window_display);
        makeUnmakeSidebar(cfg);
        $("#toc_button").toggleClass('active', cfg.toc_window_display);
        if (!cfg.toc_section_display) {
            makeUnmakeMinimized(cfg);
        }
    };


    // Table of Contents ==========================
    var table_of_contents = function (cfg, st) {
        // In a live notebook, read_config will have been called already, but
        // in non-live notebooks, ensure that all config values are defined.
        if (!liveNotebook) {
            cfg = $.extend(true, {}, default_cfg, cfg);
        }
        var toc_wrapper = $("#toc-wrapper");
        if (toc_wrapper.length === 0) { // toc window doesn't exist at all
            build_side_panel(cfg, st); // create it
        }
    };

    var toggle_panel = function (cfg, st) {
        // toggle draw (first because of first-click behavior)
        var wrap = $("#toc-wrapper");
        var show = wrap.is(':hidden');
        wrap.toggle(show);
        cfg['toc_window_display'] = setMd('toc_window_display', show);
        setNotebookWidth(cfg);
        table_of_contents(cfg);
        $("#toc_button").toggleClass('active', show);
    };

    var show_settings_dialog = function (cfg, st) {

        var callback_setting_change = function (evt) {
            var input = $(evt.currentTarget);
            var md_key = input.attr('tocMdKey');
            cfg[md_key] = setMd(md_key, input.attr('type') == 'checkbox' ? Boolean(input.prop('checked')) : input.val());
            table_of_contents(cfg, st);
        };
        var build_setting_input = function (md_key, md_label, input_type) {
            var opts = liveNotebook ? IPython.notebook.metadata.toc : cfg;
            var id = 'toc-settings-' + md_key;
            var fg = $('<div>').append(
                $('<label>').text(md_label).attr('for', id));
            var input = $('<input/>').attr({
                type: input_type || 'text', id: id, tocMdKey: md_key,
            }).on('change', callback_setting_change);
            if (input_type == 'checkbox') {
                fg.addClass('checkbox');
                input
                    .prop('checked', opts[md_key])
                    .prependTo(fg.children('label'));
            } else {
                fg.addClass('form-group');
                input
                    .addClass('form-control')
                    .val(opts[md_key])
                    .appendTo(fg);
            }
            return fg;
        };

        var modal = $('<div class="modal fade" role="dialog"/>');
        var dialog_content = $("<div/>")
            .addClass("modal-content")
            .appendTo($('<div class="modal-dialog">').appendTo(modal));
        $('<div class="modal-header">')
            .append('<button type="button" class="close" data-dismiss="modal" aria-hidden="true">&times;</button>')
            .append('<h4 class="modal-title">panel settings</h4>')
            .on('mousedown', function () {
                $('.modal').draggable({handle: '.modal-header'});
            })
            .appendTo(dialog_content);
        $('<div>')
            .addClass('modal-body')
            .append([
                $('<div>').text(
                    'These settings apply to this notebook only, and are stored in its metadata. ' +
                    liveNotebook ? 'The defaults for new notebooks can be edited from the nbextensions configurator.' :
                        'The settings won\'t persist in non-live notebooks though.'),
                build_setting_input('sideBar', 'Display as a sidebar (otherwise as a floating window)', 'checkbox'),
                build_setting_input('toc_window_display', 'Display ToC window/sidebar at startup', 'checkbox'),
                build_setting_input('toc_section_display', 'Expand window/sidebar at startup', 'checkbox'),
            ])
            .appendTo(dialog_content);
        $('<div class="modal-footer">')
            .append('<button class="btn btn-default btn-sm btn-primary" data-dismiss="modal">Ok</button>')
            .appendTo(dialog_content);
        // focus button on open
        modal.on('shown.bs.modal', function () {
            setTimeout(function () {
                dialog_content.find('.modal-footer button').last().focus();
            }, 0);
        });

        if (liveNotebook) {
            Jupyter.notebook.keyboard_manager.disable();
            modal.on('hidden.bs.modal', function () {
                modal.remove(); // destroy modal on hide
                Jupyter.notebook.keyboard_manager.enable();
                Jupyter.notebook.keyboard_manager.command_mode();
                var cell = Jupyter.notebook.get_selected_cell();
                if (cell) cell.select();
            });
        }

        // Try to use bootstrap modal, but bootstrap's js may not be available
        try {
            return modal.modal({backdrop: 'static'});
        } catch (err) {
            // show the backdrop
            $(document.body).addClass('modal-open');
            var $backdrop = $('<div class="modal-backdrop fade">').appendTo($(document.body));
            $backdrop[0].offsetWidth; // force reflow
            $backdrop.addClass('in');
            // hook up removals
            modal.on('click', '[data-dismiss="modal"]', function modal_close() {
                // hide the modal foreground
                modal.removeClass('in');
                setTimeout(function on_foreground_hidden() {
                    modal.remove();
                    // now hide the backdrop
                    $backdrop.removeClass('in');
                    // wait for transition
                    setTimeout(function on_backdrop_hidden() {
                        $(document.body).removeClass('modal-open');
                        $backdrop.remove();
                    }, 150);
                }, 300);
            });
            // wait for transition
            setTimeout(function () {
                // now show the modal foreground
                modal.appendTo(document.body).show().scrollTop(0);
                modal[0].offsetWidth; // force reflow
                modal.addClass('in');
                // wait for transition, then trigger callbacks
                setTimeout(function on_foreground_shown() {
                    modal.trigger('shown.bs.modal');
                }, 300);
            }, 150);
            return modal;
        }
    };

    return {
        table_of_contents: table_of_contents,
        toggle_panel: toggle_panel,
        read_config: read_config,
        receiveMessageInit: receiveMessageInit
    };
});
//export table_of_contents to global namespace for backwards compatibility
//异步导出，准备好内容再渲染
if (!requirejs.specified('base/js/namespace')) {
    window.table_of_contents = function (cfg, st) {
        "use strict";
        // use require to ensure the module is correctly loaded before the
        // actual call is made
        requirejs(['nbextensionsnbextensions/toggle_iframe/toc2'], function (toc2) {
            toc2.table_of_contents(cfg, st);
        });
    };
}
