import {seasons} from "./seasons";
import {min_max} from "./utils";


export let GraphBase = function(container_selector, edges, x_margin) {

    edges = edges || {top: 20, right: 40, bottom: 20, left: 64}; // Spacing inside canvas to graph ares.
    x_margin = x_margin || 20;                                   // Extra spacing on x inside axis, but inside edge.
    
    var o = {};

    //
    // Fixed values.
    //
    
    o.container = $(container_selector);
    o.canvas = $('.graph', o.container);
    o.tooltip = $('.tooltip', o.container);
    o.ctx = o.canvas[0].getContext("2d");
    
    o.edges = edges;

    o.x_margin = x_margin;

    //
    // Calculated after resize or settings changes.
    //

    o.settings = {};
    o.initialized = false;
    o.use_crosshair = true;
    
    o.width = 100;
    o.height = 100;

    o.y_ax = {};
    o.y_ax.top_value;    // The actual value at the top of the graph.
    o.y_ax.bottom_value; // The actual value at the botttom of the graph.
    o.y_per_unit;        // Y-pixels per unit whatever it is.

    o.x_ax = {};
    o.x_ax.left_value;  // The actual leftmost value.
    o.x_ax.right_value; // The actual rightmost value.
    o.x_per_unit;       // X-pixels per unit whatever it is.

    o.points; // Points on the graph, used for mouse over functionality.

    o.race_colors = {};
    o.race_colors[-1] = '#666666'; // Unknown
    o.race_colors[0]  = '#704898'; // Zerg
    o.race_colors[1]  = '#fff080'; // Protoss
    o.race_colors[2]  = '#c94118'; // Terran
    o.race_colors[3]  = '#a0ebff'; // Random
    
    //
    // Drawing functions.
    //

    // Clear, fill canvas with black.
    o.clear = function(alpha) {
        alpha = alpha || 1.0;
        o.ctx.globalAlpha = alpha;
        o.ctx.fillStyle = "#000000";
        o.ctx.fillRect(0, 0, o.canvas.width(), o.canvas.height());
        o.ctx.globalAlpha = 1.0;
    };

    // Creates a gradient (tied to the context).
    o.gradient = function(color0, color1) {
        var gradient = o.ctx.createLinearGradient(0, 0, o.width, o.height);
        gradient.addColorStop(0.0, color0);
        gradient.addColorStop(0.2, color1);
        gradient.addColorStop(0.4, color0);
        gradient.addColorStop(0.5, color1);
        gradient.addColorStop(0.6, color0);
        gradient.addColorStop(0.8, color1);
        gradient.addColorStop(0.9, color0);
        gradient.addColorStop(1.0, color1);
        return gradient
    };

    // Initialize styles for the league colors, needs to be done after each resize.
    o.setup_league_styles = function() {
        o.bronze = o.gradient('#5d3621', '#3d1f17');
        o.silver = o.gradient('#606060', '#808080');
        o.gold = o.gradient('#e8e8e8', '#e8b830');
        o.platinum = o.gradient('#a0a0a0', '#e0e0e0');
        o.diamond = o.gradient('#2080c0', '#3040a0');
        o.master = o.gradient('#078786', '#5aeeee');
        o.grandmaster = '#ff0000';
        o.league_styles = [o.bronze, o.silver, o.gold, o.platinum, o.diamond, o.master, o.grandmaster]
    };

    // Graph line helper.
    o._line_helper = function(points, x_offset, y_offset) {
        x_offset = x_offset || 0;
        y_offset = y_offset || 0;
        o.ctx.beginPath();
        o.ctx.moveTo(points[0].x + x_offset, points[0].y + y_offset);
        for (var i = 1; i < points.length; ++i) {
            o.ctx.lineTo(points[i].x + x_offset, points[i].y + y_offset);
        }
    };
    
    // Draw a line relative to the canvas. Points is a list of {x: x, y: y}. Add x and y offset to each point.
    o.line = function(style, width, points, x_offset, y_offset) {
        o.ctx.strokeStyle = style;
        o.ctx.lineWidth = width;
        o._line_helper(points, x_offset, y_offset);
        o.ctx.stroke();
    };

    // Same as line but points are relative to the graph area.
    o.gline = function(style, width, points) {
        o.line(style, width, points, o.edges.left, o.edges.top);
    };
    
    // Just like line but fill the area in the line with fill style.
    o.area = function(style, points, x_offset, y_offset) {
        o.ctx.fillStyle = style;
        o._line_helper(points, x_offset, y_offset);
        o.ctx.closePath();
        o.ctx.fill();
    };
 
    // Same as area but points are relative to the graph area.
    o.garea = function(style, points) {
        o.area(style, points, o.edges.left, o.edges.top);
    };

    // Just like line but text.
    o.text = function(text, x_offset, y_offset, align, baseline, style) {
        o.ctx.font ="normal 13px sans-serif ";
        o.ctx.textAlign = align || 'center';
        o.ctx.textBaseline = baseline || 'top';
        o.ctx.fillStyle = style || "#ffffff";
        o.ctx.fillText(text, x_offset, y_offset)
    };
    
    // Print the y-axis.
    o.y_axis = function(y_label) {
        y_label = y_label ||  "int";
        
        o.line("#ffffff", 2, [{x: o.edges.left - o.x_margin, y: o.edges.top},
                              {x: o.edges.left - o.x_margin, y: o.edges.top + o.height}]);
        
        for (var pos = 0; pos <= 10; ++pos) {
            var value = (o.y_ax.bottom_value - o.y_ax.top_value) / 10 * pos + o.y_ax.top_value;
            var y = Math.round(o.edges.top + (value - o.y_ax.top_value) * o.y_per_unit) + 0.5;

            var label;

            if (y_label == 'percent') {
                if (Math.max(Math.abs(o.y_ax.top_value), Math.abs(o.y_ax.bottom_value)) < 10) {
                    label = value.toFixed(2) + "%"
                }
                else if (Math.abs(o.y_ax.bottom_value - o.y_ax.top_value) < 10) {
                    label = value.toFixed(1) + "%"
                }
                else {
                    label = Math.round(value) + "%";
                }
            }
            else if (y_label == 'int') {
                if (value == 1) {
                    label = "1";
                }
                else if (o.y_ax.bottom_value > 100000 || o.y_ax.top_value > 10000) {
                    label = Math.round(value / 1000) + "k"
                }
                else {
                    label = Math.round(value);
                }
            }
            else {
                label = Math.round(value);
            }

            o.text(label, o.edges.left - o.x_margin - 5, y, "right", "middle");

            if (y < (o.edges.top + o.height - 2)) {
                o.line("#ffffff", 1, [{x: o.edges.left - o.x_margin - 3, y: y}, {x: o.edges.left - o.x_margin + 3, y: y}]);
            }
        }
    };

    // Converts epoch (in seconds) to an x value (in the graph).
    o.epoch_to_pixels = function(epoch) {
        return (epoch - o.x_ax.left_value) * o.x_per_unit;
    };

    // Converts a date to an x value (not including the edges).
    o.date_to_pixels = function(year, month, day) {
        day = day || 0;
        month = month || 0;
        return (new Date(year, month, day).getTime() / 1000 - o.x_ax.left_value) * o.x_per_unit;
    };
    
    // Print a time x-axis.
    o.time_x_axis = function(x_label) {
        x_label = x_label || "year";
        

        // Draw season colored base line and labels.

        var y = o.height;
        var x_from = -o.x_margin; // Start outside actual drawing area.
        var season;
        for (var i = 0; i < seasons.sorted.length; ++i) {
            season = seasons.sorted[i];
            if (season.end > o.x_ax.left_value && season.start < o.x_ax.right_value) {
                var x_to = Math.min(o.epoch_to_pixels(season.end), o.width);

                // Draw the colored season line, add x_margin to the end (all but the last line will be overwritten by
                // another color causing the last one to be extended just like the first one).
                o.gline(season.color, 2, [{x: x_from, y: y}, {x: x_to + o.x_margin, y: y}]);

                if (x_label == "season") {
                    var label = "Season " + season.id + " (" + season.number + " - " + season.year + ")";
                    var label_width = o.ctx.measureText(label).width;
                    var width = x_to - x_from;
                    if (width > label_width) {
                        var x = min_max(width / 2, x_from + width / 2, o.width - label_width / 2);
                        o.text(label, o.edges.left + x, o.edges.top + o.height + 3, 'center', 'top');
                    }
                }
                x_from = x_to;
            }
        }

        // Print years/months and year lines.
        
        var months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

        function pixel_to_date(x) {
            return new Date((x / o.x_per_unit + o.x_ax.left_value) * 1000);
        }
        
        var start_year = pixel_to_date(-o.x_margin).getFullYear();
        var end_year = pixel_to_date(o.width + o.x_margin).getFullYear();
        
        for (var year = start_year; year <= end_year; ++year) {

            var year_x = o.date_to_pixels(year);
            if (year_x > -o.x_margin && year_x < o.width + o.x_margin) {
                o.gline("#ffffff", 2, [{x: year_x, y: o.height - 7}, {x: year_x, y: o.height + 7}]);
            }
            
            for (var month = 0; month < 12; ++month) {
                var month_start_x = Math.round(o.date_to_pixels(year, month)) + 0.5;
                var month_end_x = Math.round(o.date_to_pixels(year, month + 1)) + 0.5;

                // Month bar.
                if (month_start_x > -o.x_margin && month_start_x < o.width + o.x_margin) {
                    o.gline("#ffffff", 1, [{x: month_start_x, y: o.height - 3}, {x: month_start_x, y: o.height + 3}]);
                }

                // Month label.
                var text_width = o.ctx.measureText(year).width;
                if (x_label == 'month' && month_end_x > text_width / 2 && month_start_x < o.width - text_width / 2) {
                    var text_x = min_max(0, (month_end_x - month_start_x) / 2 + month_start_x, o.width);
                    o.text(months[month], o.edges.left + text_x, o.edges.top + o.height + 3, 'center', 'top');
                }
            }

            // Draw lotv release line.

            var lotv_label = "LotV Release";
            var lotv_release_x = o.date_to_pixels(2015, 10, 9);
            if (lotv_release_x - 10 > 0 && lotv_release_x + 10 < o.width) {
                o.gline('#ffff00', 2, [{x: lotv_release_x, y: o.height + 5}, {x: lotv_release_x, y: o.height - 5}]);
                o.text(lotv_label, o.edges.left + lotv_release_x, o.edges.top + o.height + 3 , 'center', 'top', '#ffff00');
            }
        
            // Year label.
            if (x_label == 'year') {
                var label_x = min_max(o.ctx.measureText(year).width / 2,
                                      o.date_to_pixels(year, 6),
                                      o.width - o.ctx.measureText(year).width / 2);
                o.text(year, o.edges.left + label_x, o.edges.top + o.height + 3, 'center', 'top');
            }
        }
    };

    // Draw crosshair.
    o.draw_crosshair = function() {
        if (o.crosshair) {
            var x = Math.round(o.crosshair.x + o.edges.left) + 0.5;
            var y = Math.round(o.crosshair.y + o.edges.top) + 0.5;
            o.line("#ffffff", 1, [{x: 0, y: y}, {x: o.canvas.width(), y: y}]);
            o.line("#ffffff", 1, [{x: x, y: 0}, {x: x, y: o.canvas.height()}]);
       }
    };
    
    // Generic controls change value, use this for callback when registring controls.
    o.controls_change = function(name, value) {
        o.settings[name] = value;

        if (o.initialized) {
            o.new_settings();
            o.redraw();
        }
    };

    // Show mouse stuff.
    o.mouse_on = function(x, y, m) {
        var offset = o.canvas.offset();
        var width = o.update_tooltip(m);
        o.tooltip.show();
        o.tooltip.offset({left: offset.left + Math.min(x + o.edges.left + 20, o.canvas.width() - width - 10),
                          top: offset.top + y + o.edges.top + 20});
        o.crosshair = {x: x, y: y};
        if (o.use_crosshair) {
            o.redraw();
        }
    };

    // Show mouse stuff.
    o.mouse_off = function(x, y, m) {
        o.tooltip.hide();
        if (o.use_crosshair) {
            o.redraw();
        }
        o.crosshair = undefined;
    };
    
    // Callback on mouse move.
    o.mouse_move = function(event) {
        var offset = o.canvas.offset();
        var mouse_x = event.pageX - offset.left - o.edges.left;
        var mouse_y = event.pageY - offset.top - o.edges.top;

        if (mouse_x < -o.edges.left / 2 || mouse_x > o.width + o.edges.right / 2
            || mouse_y < -o.edges.top / 2 || mouse_y > o.height + o.edges.bottom / 2) {
            o.mouse_off();
            return;
        }
        
        // Find best point.

        var min_distance = 1e9;
        var x;
        var y;
        var m;
        for (var i = 0; i < o.points.length; ++i) {
            var point = o.points[i];
            var distance = Math.pow(point.x - mouse_x, 2) + Math.pow(point.y - mouse_y, 2);
            if (distance < min_distance) {
                min_distance = distance;
                x = point.x;
                y = point.y;
                m = point.m;
            }
        }

        if (min_distance < 16 * 16) {
            o.mouse_on(x, y, m);
            return;
        }
        
        o.mouse_off();
    };

    //
    // Callbacks to implement for graphs.
    //

    o.new_settings; // Calculate everyhing needed after new settings. New settings will be set on o.

    o.new_size; // Calculate everything needed after new size. New size will be set on o.

    o.redraw; // Redraw the graph.

    o.update_tooltip; // Update the tooltip data.

    //
    // Functions.
    //

    // Resize canwas based on 0.30 proportions.
    o.resize_canvas = function() {
        o.canvas[0].width = o.container.width();
        o.canvas[0].height = Math.max(280, Math.round(o.container.width() * 0.30));
    };
    
    // Set new size, call new_size and redraw.
    o.resize = function() {
        o.resize_canvas();
        
        o.width = o.canvas.width() - o.edges.left - o.edges.right;
        o.height = o.canvas.height() - o.edges.top - o.edges.bottom;

        o.new_size();
        o.redraw();
    };

    // Init everything based on the data requested/provided in the constructor.
    o.init = function() {
        window.addEventListener('resize', o.resize, false);
        o.new_settings();
        o.resize();

        o.canvas.on('mousemove', o.mouse_move);
        
        o.container.removeClass('wait');
        o.initialized = true;
    };

    o.resize_canvas();
    
    return o;
};
