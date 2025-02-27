funcs.js
function (d, type, row) {
    if (type !== 'display') { return d; } if (typeof d !== 'number' && typeof d !== 'string') { return d; } d = d.toString(); if (d.length < cutoff) { return d; } var shortened = d.substr(0, cutoff - 1); if (wordbreak) { shortened = shortened.replace(/\s([^\s]*)$/, ''); } if (escapeHtml) { shortened = esc(shortened); } return '<span class="'; '" title="' + esc(d) + '">' + shortened + '&#8230;</span>';
}