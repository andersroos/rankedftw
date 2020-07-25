import {seasons} from "./seasons";
import {min_max} from "./utils";

// Base class for all graphs.
export class GraphBase {
    
    // Create graph container should be a div with canvas.graph and .controls inside.
    constructor(container_selector, edges, x_margin) {
        this.edges = edges || {top: 20, right: 40, bottom: 20, left: 64}; // Spacing inside canvas to start of graph.
        this.x_margin = x_margin || 20;                                   // Extra x spacing inside y-axis on left and inside edge on right.
    
        this.container = document.querySelector(container_selector);
        this.canvas = this.container.querySelector(".graph");
        this.tooltip = this.container.querySelector(".tooltip");
        this.ctx = this.canvas.getContext("2d");
    
        //
        // Calculated after resize or settings changes.
        // TODO Move to where they are changed=
        //
    
        this.settings = {};
        this.initialized = false;  // Try to remove.
    
        this.width = 100;          // With of the canvas.
        this.height = 100;         // Height of the canvas.
    
        this.y_ax = {
            top_value: null,       // The actual value at the top of the graph.
            bottom_value: null,    // The actual value at the bottom of the graph.
        };
        this.y_per_unit = null;    // Y-pixels per unit whatever it is.
    
        this.x_ax = {
            left_value: null,      // The actual leftmost value.
            right_value: null,     // The actual rightmost value.
        };
        this.x_per_unit = null;    // X-pixels per unit whatever it is.
    
        this.points = null;        // Array of points on the graph, used for mouse over functionality.
    
        this.crosshair = null;     // Crosshair coordinates when shown.
    
        this.resize_canvas(); // TODO Figure out how things should be initialized.
    }
    
    //
    // Drawing methods.
    //
    
    // Clear, fill canvas with black using apha.
    clear(alpha) {
        alpha = alpha || 1.0;
        this.ctx.globalAlpha = alpha;
        this.ctx.fillStyle = "#000000";
        this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);
        this.ctx.globalAlpha = 1.0;
    }
    
    // Initialize styles for the league colors, needs to be done after each resize.
    setup_league_styles() {
        const make_league_style = (color0, color1) => {
            const gradient = this.ctx.createLinearGradient(0, 0, this.width, this.height);
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
        const bronze = make_league_style('#5d3621', '#3d1f17');
        const silver = make_league_style('#606060', '#808080');
        const gold = make_league_style('#e8e8e8', '#e8b830');
        const platinum = make_league_style('#a0a0a0', '#e0e0e0');
        const diamond = make_league_style('#2080c0', '#3040a0');
        const master = make_league_style('#078786', '#5aeeee');
        const grandmaster = '#ff0000';
        this.league_styles = [bronze, silver, gold, platinum, diamond, master, grandmaster]
    }
    
    // Draw a canvas line, can be used for lines or polygons.
    raw_canvas_line(points, x_offset, y_offset) {
        x_offset = x_offset || 0;
        y_offset = y_offset || 0;
        this.ctx.beginPath();
        this.ctx.moveTo(points[0].x + x_offset, points[0].y + y_offset);
        for (let i = 1; i < points.length; ++i) {
            this.ctx.lineTo(points[i].x + x_offset, points[i].y + y_offset);
        }
    }
    
    // Draw a line relative to the canvas. Points is a list of {x: x, y: y}. Add x and y offset to each point.
    line(style, width, points, x_offset, y_offset) {
        this.ctx.strokeStyle = style;
        this.ctx.lineWidth = width;
        this.raw_canvas_line(points, x_offset, y_offset);
        this.ctx.stroke();
    }
    
    // Same as line but points are relative to the graph area.
    gline(style, width, points) {
        this.line(style, width, points, this.edges.left, this.edges.top);
    }
    
    // Just like line but fill the area in the line with fill style.
    area(style, points, x_offset, y_offset) {
        this.ctx.fillStyle = style;
        this.raw_canvas_line(points, x_offset, y_offset);
        this.ctx.closePath();
        this.ctx.fill();
    }
    
    // Same as area but points are relative to the graph area.
    garea(style, points) {
        this.area(style, points, this.edges.left, this.edges.top);
    }
    
    // Just like line but text.
    text(text, x_offset, y_offset, align, baseline, style) {
        this.ctx.font ="normal 13px sans-serif ";
        this.ctx.textAlign = align || 'center';
        this.ctx.textBaseline = baseline || 'top';
        this.ctx.fillStyle = style || "#ffffff";
        this.ctx.fillText(text, x_offset, y_offset)
    }
    
    // Draw the y-axis, y_axis_type can be "int" or "percent", the direction of the int or percent is decided by the values.
    y_axis(y_axis_type) {
        y_axis_type = y_axis_type ||  "int";
        
        this.line("#ffffff", 2, [{x: this.edges.left - this.x_margin, y: this.edges.top}, {x: this.edges.left - this.x_margin, y: this.edges.top + this.height}]);
        
        for (let pos = 0; pos <= 10; ++pos) {
            const value = (this.y_ax.bottom_value - this.y_ax.top_value) / 10 * pos + this.y_ax.top_value;
            const y = Math.round(this.edges.top + (value - this.y_ax.top_value) * this.y_per_unit) + 0.5;
            
            let label;
            
            if (y_axis_type === 'percent') {
                if (Math.max(Math.abs(this.y_ax.top_value), Math.abs(this.y_ax.bottom_value)) < 10) {
                    label = value.toFixed(2) + "%"
                }
                else if (Math.abs(this.y_ax.bottom_value - this.y_ax.top_value) < 10) {
                    label = value.toFixed(1) + "%"
                }
                else {
                    label = Math.round(value) + "%";
                }
            }
            else if (y_axis_type === 'int') {
                if (value === 1) {
                    label = "1";
                }
                else if (this.y_ax.bottom_value > 100000 || this.y_ax.top_value > 10000) {
                    label = Math.round(value / 1000) + "k"
                }
                else {
                    label = Math.round(value);
                }
            }
            else {
                label = Math.round(value);
            }
            
            this.text(label, this.edges.left - this.x_margin - 5, y, "right", "middle");
            
            if (y < (this.edges.top + this.height - 2)) {
                this.line("#ffffff", 1, [{x: this.edges.left - this.x_margin - 3, y: y}, {x: this.edges.left - this.x_margin + 3, y: y}]);
            }
        }
    }
    
    // Converts epoch (in seconds) to an x value (in the graph).
    epoch_to_pixels(epoch) {
        return (epoch - this.x_ax.left_value) * this.x_per_unit;
    }
    
    // Converts a date to an x value (not including the edges).
    date_to_pixels(year, month, day) {
        day = day || 0;
        month = month || 0;
        return (new Date(year, month, day).getTime() / 1000 - this.x_ax.left_value) * this.x_per_unit;
    }

    // Convert x value to date.
    pixel_to_date(x) {
        return new Date((x / this.x_per_unit + this.x_ax.left_value) * 1000);
    }
    
    // Draw a time x-axis, x_axis_type can be "year" (year labels), "season" (season labels) or "month" (month labels).
    time_x_axis(x_axis_type) {
        x_axis_type = x_axis_type || "year";
        
        // Draw season colored base line and labels.
        
        const y = this.height;
        let x_from = -this.x_margin; // Start outside actual drawing area.
        let season;
        for (let i = 0; i < seasons.sorted.length; ++i) {
            season = seasons.sorted[i];
            if (season.end >= this.x_ax.left_value && season.start <= this.x_ax.right_value) {
                const x_to = Math.min(this.epoch_to_pixels(season.end), this.width);
                
                // Draw the colored season line, add x_margin to the end (all but the last line will be overwritten by
                // another color causing the last one to be extended just like the first one).
                this.gline(season.color, 2, [{x: x_from, y: y}, {x: x_to + this.x_margin, y: y}]);
                
                if (x_axis_type === "season") {
                    let label = "Season " + season.id + " (" + season.number + " - " + season.year + ")";
                    let label_width = this.ctx.measureText(label).width;
                    let width = x_to - x_from;
                    if (width > label_width) {
                        const x = min_max(width / 2, x_from + width / 2, this.width - label_width / 2);
                        this.text(label, this.edges.left + x, this.edges.top + this.height + 3, 'center', 'top');
                    }
                }
                x_from = x_to;
            }
        }
        
        // Print years/months and year lines.
        
        let months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
        
        let start_year = this.pixel_to_date(-this.x_margin).getFullYear();
        let end_year = this.pixel_to_date(this.width + this.x_margin).getFullYear();
        
        for (let year = start_year; year <= end_year; ++year) {
            
            let year_x = this.date_to_pixels(year);
            if (year_x > -this.x_margin && year_x < this.width + this.x_margin) {
                this.gline("#ffffff", 2, [{x: year_x, y: this.height - 7}, {x: year_x, y: this.height + 7}]);
            }
            
            for (let month = 0; month < 12; ++month) {
                let month_start_x = Math.round(this.date_to_pixels(year, month)) + 0.5;
                let month_end_x = Math.round(this.date_to_pixels(year, month + 1)) + 0.5;
                
                // Month bar.
                if (month_start_x > -this.x_margin && month_start_x < this.width + this.x_margin) {
                    this.gline("#ffffff", 1, [{x: month_start_x, y: this.height - 3}, {x: month_start_x, y: this.height + 3}]);
                }
                
                // Month label.
                let text_width = this.ctx.measureText(year).width;
                if (x_axis_type === 'month' && month_end_x > text_width / 2 && month_start_x < this.width - text_width / 2) {
                    let text_x = min_max(0, (month_end_x - month_start_x) / 2 + month_start_x, this.width);
                    this.text(months[month], this.edges.left + text_x, this.edges.top + this.height + 3, 'center', 'top');
                }
            }
            
            // Year label.
            if (x_axis_type === 'year') {
                let label_x = min_max(this.ctx.measureText(year).width / 2,
                    this.date_to_pixels(year, 6),
                    this.width - this.ctx.measureText(year).width / 2);
                this.text(year, this.edges.left + label_x, this.edges.top + this.height + 3, 'center', 'top');
            }
        }
        
        // Draw lotv release line and mmr avaiable line.
        
        const draw_event_line =(label, yr, m, d) => {
            const x = this.date_to_pixels(yr, m, d);
            this.gline('#ffff00', 2, [{x: x, y: this.height + 5}, {x: x, y: this.height - 5}]);
            this.text(label, this.edges.left + x, this.edges.top + this.height - 5 , 'center', 'bottom', '#ffff00');
        };
        
        draw_event_line("LotV", 2015, 10, 9);
        draw_event_line("MMR", 2016, 6, 17);
        draw_event_line("f2p", 2017, 10, 15);
    }
    
    
    // Draw crosshair.
    draw_crosshair() {
        if (this.crosshair) {
            const x = Math.round(this.crosshair.x + this.edges.left) + 0.5;
            const y = Math.round(this.crosshair.y + this.edges.top) + 0.5;
            this.line("#ffffff", 1, [{x: 0, y: y}, {x: this.canvas.width, y: y}]);
            this.line("#ffffff", 1, [{x: x, y: 0}, {x: x, y: this.canvas.height}]);
        }
    }
    
    // Generic controls change value, use this for callback when registring controls.
    // TODO Is this a good way to do this? Rename to on_controls_change??
    controls_change(name, value) {
        this.settings[name] = value;
        
        if (this.initialized) {
            this.new_settings();
            this.redraw();
        }
    }
    
    // Show tooltip and crosshair.
    mouse_on(x, y, m) {
        const width = this.update_tooltip(m);  // TODO What?? Return value? Document this.
        this.tooltip.style.display = "block";
        const absolute_x = this.canvas.offsetLeft + Math.min(x + this.edges.left + 20, this.canvas.width - width - 10);
        const absolute_y = this.canvas.offsetTop + y + this.edges.top + 20;
        this.tooltip.style.left = `${absolute_x}px`;
        this.tooltip.style.top = `${absolute_y}px`;
        this.crosshair = {x: x, y: y};
        this.redraw();
    }
    
    // Hide tooltop and crosshair.
    mouse_off() {
        this.tooltip.style.display = "none";
        this.redraw();
        this.crosshair = null;  // TODO Why this after redraw?
    }
    
    // Callback on mouse move.
    on_mouse_move(event) {
        const mouse_x = event.offsetX - this.edges.left;
        const mouse_y = event.offsetY - this.edges.top;
        
        // Check if mouse is inside graph.
        if (mouse_x < -this.edges.left / 2 || mouse_x > this.width + this.edges.right / 2
            || mouse_y < -this.edges.top / 2 || mouse_y > this.height + this.edges.bottom / 2) {
            this.mouse_off();
            return;
        }
        
        // Find point closest to pointer.
        let min_distance = 1e9;
        let x;
        let y;
        let m;
        for (let i = 0; i < this.points.length; ++i) {
            const point = this.points[i];
            const distance = Math.pow(point.x - mouse_x, 2) + Math.pow(point.y - mouse_y, 2);
            if (distance < min_distance) {
                min_distance = distance;
                x = point.x;
                y = point.y;
                m = point.m;
            }
        }
        
        // Turn on tooltip and crosshair if distance is less than 16.
        if (min_distance < 16 * 16) {
            this.mouse_on(x, y, m);
            return;
        }
        
        this.mouse_off();
    }
    
    //
    // Callbacks to implement for graphs.
    //
    
    // Calculate everyhing needed after new settings. New settings will be set on o.
    new_settings() {
        throw new Error("method needs to be implemented for graph");
    }
    
    // Calculate everything needed after new size. New size will be set on this.
    new_size() {
        throw new Error("method needs to be implemented for graph");
    }
    
    // Redraw the graph.
    redraw() {
        throw new Error("method needs to be implemented for graph");
    }
    
    // Update the tooltip data.
    update_tooltip() {
        throw new Error("method needs to be implemented for graph");
    }
    
    //
    // Functions. TODO ????
    //
    
    // Resize canwas based on 0.30 proportions.
    resize_canvas() {
        this.canvas.width = this.container.offsetWidth;
        this.canvas.height = Math.max(280, Math.round(this.container.offsetWidth * 0.30));
    }
    
    // Set new size, call new_size and redraw.
    resize() {
        this.resize_canvas();
        
        this.width = this.canvas.width - this.edges.left - this.edges.right;
        this.height = this.canvas.height - this.edges.top - this.edges.bottom;
        
        this.new_size();
        this.redraw();
    }
    
    // Init everything based on the data requested/provided in the constructor.
    init() {
        window.onresize = () => this.resize();
        this.new_settings();
        this.resize();
        
        this.canvas.onmousemove = e => this.on_mouse_move(e);
        
        this.container.classList.remove("wait");
        this.initialized = true;
    }
}
