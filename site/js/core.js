
//
// Utils.
//

let sc2 = {};

sc2.utils = {};

//
// HTML
//

sc2.html = {}; 

// // Add classes to container.
// sc2.html.conf_container = function(jq_container) {
//     jq_container.addClass('data-container wait');
// };
//
// // Add controls to container and returns of controls container.
// sc2.html.add_controls_div = function(jq_container) {
//     var controls = $('<div class="controls">');
//     var content = $('<div class="content">');
//     controls.append(content);
//     jq_container.append(controls);
//     return content;
// };
//
// // Add a control to controls. Buttons is a list of {value: <value>, tooltip:
// // <tooltip>, heading: <heading>, src: <optional heading img source>}.
// sc2.html.add_control = function(jq_controls, name, heading, options) {
//     var ul = $("<ul ctrl-name='" + name + "'>");
//     ul.append("<span>" + heading + "</span>");
//     for (var i = 0; i < options.length; ++i) {
//         var a = $("<a ctrl-value='" + options[i].value + "' title='" + options[i].tooltip + "'>");
//         a.append("<span>" + options[i].heading + "</span>");
//         if (options[i].src) {
//             a.append("<img src='" + options[i].src + "'>");
//         }
//         ul.append(a);
//     }
//     jq_controls.append(ul);
// };
//
// // Add canvas element to container.
// sc2.html.add_canvas = function(jq_container) {
//     jq_container.append('<canvas class="graph">');
// };
//
// // Add tooltip element to container. Table is a list of <heading, data-class>.
// sc2.html.add_tooltip = function(jq_container, data) {
//     var tooltip = $('<div class="tooltip">');
//     var table = $('<table>');
//     for (var i = 0; i < data.length; ++i) {
//         var tr = $('<tr>');
//         tr.append("<th>" + data[i][0] + "</th>");
//         tr.append("<td class='" + data[i][1] + "'></td>");
//         table.append(tr);
//     }
//     tooltip.append(table);
//     jq_container.append(tooltip);
// };


// //
// // Common graph stuff.
// //
//
// sc2.graph = {};
//
// // Insert image tags for resources listed in options ("leagues") and
// // call success when loaded.
// sc2.graph.load_resources = function(container_selector, options, success) {
//
// };

    
// export let seasons = sc2.seasons;