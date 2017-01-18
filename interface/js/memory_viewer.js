
var editableGrid = null;

function addHoverMemoryView() {
  $("#memoryview td").each(function (idx, e) {
    var suffix = this.classList[0].slice(-2);
    if (suffix[0] == 'c') { suffix = suffix.slice(-1); }
    suffix = parseInt(suffix);
    if (!isNaN(suffix)) {
      suffix = suffix.toString(16);
      var addr = $('td:first', $(e).closest('tr')).text().slice(0,9) + suffix;
      $(e).tooltipster({
        content: 'Adresse: ' + addr,
        position: 'top'
      });
    }
  });
}


function updateMemoryBreakpointsView() {
  for (var i = 0; i < mem_breakpoints_r.length; i++) {
    tofind = formatHexUnsigned32Bits(mem_breakpoints_r[i]).slice(0, 9) + "0";
    var tableRow = $("td", $("#memoryview")).filter(function() {
      return $(this).text() == tofind;
    }).closest("tr");
    if (tableRow.length < 1) {
      continue;
    }
    col = parseInt(mem_breakpoints_r[i], 16) % 16;
    $('.editablegrid-c'+col, tableRow).addClass('mem_r');
  }

  for (var i = 0; i < mem_breakpoints_w.length; i++) {
    tofind = formatHexUnsigned32Bits(mem_breakpoints_w[i]).slice(0, 9) + "0";
    var tableRow = $("td", $("#memoryview")).filter(function() {
      return $(this).text() == tofind;
    }).closest("tr");
    if (tableRow.length < 1) {
      continue;
    }
    col = parseInt(mem_breakpoints_w[i], 16) % 16;
    $('.editablegrid-c'+col, tableRow).addClass('mem_w');
  }

  for (var i = 0; i < mem_breakpoints_rw.length; i++) {
    tofind = formatHexUnsigned32Bits(mem_breakpoints_rw[i]).slice(0, 9) + "0";
    var tableRow = $("td", $("#memoryview")).filter(function() {
      return $(this).text() == tofind;
    }).closest("tr");
    if (tableRow.length < 1) {
      continue;
    }
    col = parseInt(mem_breakpoints_rw[i], 16) % 16;
    $('.editablegrid-c'+col, tableRow).addClass('mem_rw');
  }

  for (var i = 0; i < mem_breakpoints_e.length; i++) {
    tofind = formatHexUnsigned32Bits(mem_breakpoints_e[i]).slice(0, 9) + "0";
    var tableRow = $("td", $("#memoryview")).filter(function() {
      return $(this).text() == tofind;
    }).closest("tr");
    if (tableRow.length < 1) {
      continue;
    }
    col = parseInt(mem_breakpoints_e[i], 16) % 16;
    $('.editablegrid-c'+col, tableRow).addClass('mem_e');
  }

  /* Highlight current instruction */
  for (var i = 0; i < mem_breakpoints_instr.length; i++) {
    tofind = formatHexUnsigned32Bits(mem_breakpoints_instr[i]).slice(0, 9) + "0";
    var tableRow = $("td", $("#memoryview")).filter(function() {
      return $(this).text() == tofind;
    }).closest("tr");
    if (tableRow.length > 0) {
      col = mem_breakpoints_instr[i] % 16;
      $('.editablegrid-c'+col, tableRow).addClass('mem_instr');
    }
  }
}

$(document).ready(function() {
  EditableGrid.prototype.updatePaginator = function()
  {
    var paginator = $("#paginator").empty();
    var nbPages = this.getPageCount();

      // "first" link
      var link = $("<a>").html("<img src='" + image("gofirst.png") + "' style='height: 15px; vertical-align: middle;'/>&nbsp;");
      if (!this.canGoBack()) link.css({ opacity : 0.4,  filter: "alpha(opacity=40)" });
      else link.css("cursor",  "pointer").click(function(event) { editableGrid.firstPage(); addHoverMemoryView(); });
      paginator.append(link);

      // "prev" link
      link = $("<a>").html("<img src='" + image("prev.png") + "' style='height: 15px; vertical-align: middle;'/>&nbsp;");
      if (!this.canGoBack()) link.css({ opacity : 0.4,  filter: "alpha(opacity=40)" });
      else link.css("cursor",  "pointer").click(function(event) { editableGrid.prevPage(); addHoverMemoryView(); });
      paginator.append(link);

      var mem_begin = $(".editablegrid-ch:eq(1)").text();
      paginator.append('<input id="jump_memory" type="text" value="' + mem_begin + '"/><input id="jump_memory_go" type="submit" value="Go">');
      $("#jump_memory_go").click(function () {
        var target = $("#jump_memory").val();
        var page = Math.floor(parseInt(target) / (16*20));
        editableGrid.setPageIndex(page);
        addHoverMemoryView();
      });

      // "next" link
      link = $("<a>").html("<img src='" + image("next.png") + "' style='height: 15px; vertical-align: middle;'/>&nbsp;");
      if (!this.canGoForward()) link.css({ opacity : 0.4,  filter: "alpha(opacity=40)" });
      else link.css("cursor",  "pointer").click(function(event) { editableGrid.nextPage(); addHoverMemoryView(); });
      paginator.append(link);

      // "last" link
      link = $("<a>").html("<img src='" + image("golast.png") + "' style='height: 15px; vertical-align: middle;'/>&nbsp;");
      if (!this.canGoForward()) link.css({ opacity : 0.4,  filter: "alpha(opacity=40)" });
      else link.css("cursor",  "pointer").click(function(event) { editableGrid.lastPage(); addHoverMemoryView(); });
      paginator.append(link);

      $(".editablegrid-c0, .editablegrid-c1, .editablegrid-c2, .editablegrid-c3, .editablegrid-c4, .editablegrid-c5, .editablegrid-c6, .editablegrid-c7, .editablegrid-c8, .editablegrid-c9, .editablegrid-c10, .editablegrid-c11, .editablegrid-c12, .editablegrid-c13, .editablegrid-c14, .editablegrid-c15").click(function(e) {
        var suffix = this.classList[0].slice(-2);
        if (suffix[0] == 'c') { suffix = suffix.slice(-1); }
        suffix = parseInt(suffix).toString(16);
        var addr = $('td:first', $(e.target).closest('tr')).text().slice(0,9) + suffix;
        if(e.shiftKey) {
          sendCmd(['breakpointsmem', addr, 'r']);
        }
        if(e.ctrlKey) {
          sendCmd(['breakpointsmem', addr, 'w']);
        }
        if(e.altKey) {
          sendCmd(['breakpointsmem', addr, 'e']);
        }
      });
    };


  // Memory viewer
  var metadata = [];
  metadata.push({ name: "ch",  label: "addr",  datatype: "string",  editable: false});
  metadata.push({ name: "c0",  label: "00",  datatype: "string",  editable: true});
  metadata.push({ name: "c1",  label: "01",  datatype: "string",  editable: true});
  metadata.push({ name: "c2",  label: "02",  datatype: "string",  editable: true});
  metadata.push({ name: "c3",  label: "03",  datatype: "string",  editable: true});
  metadata.push({ name: "c4",  label: "04",  datatype: "string",  editable: true});
  metadata.push({ name: "c5",  label: "05",  datatype: "string",  editable: true});
  metadata.push({ name: "c6",  label: "06",  datatype: "string",  editable: true});
  metadata.push({ name: "c7",  label: "07",  datatype: "string",  editable: true});
  metadata.push({ name: "c8",  label: "08",  datatype: "string",  editable: true});
  metadata.push({ name: "c9",  label: "09",  datatype: "string",  editable: true});
  metadata.push({ name: "c10",  label: "0A",  datatype: "string",  editable: true});
  metadata.push({ name: "c11",  label: "0B",  datatype: "string",  editable: true});
  metadata.push({ name: "c12",  label: "0C",  datatype: "string",  editable: true});
  metadata.push({ name: "c13",  label: "0D",  datatype: "string",  editable: true});
  metadata.push({ name: "c14",  label: "0E",  datatype: "string",  editable: true});
  metadata.push({ name: "c15",  label: "0F",  datatype: "string",  editable: true});

  // Not necessary?
  var data = [];
  for (var i = 0; i < 20; i++) {
    data.push({id: i,  values: {"c0": "00",  "c1": "00",  "c2": "00",  "c3": "00",  "c4": "00",  "c5": "00",  "c6": "00",  "c7": "00",  "c8": "00",  "c9": "00",  "c10": "00",  "c11": "00",  "c12": "00",  "c13": "00",  "c14": "00",  "c15": "00"}});
    data[i]["values"]["ch"] = formatHexUnsigned32Bits(i*16)
  }

  editableGrid = new EditableGrid("DemoGridJsData",  {
    modelChanged: function(row, col, oldValue, newValue, rowref) { 
      if (oldValue !== "--") {
        console.log("Here!");
        var addr = parseInt($("td:first", rowref).text(), 16) + (columnIndex - 1)
        sendCmd(['memchange', addr, newValue]);
      } else {
        editableGrid.setValueAt(row, col, "--", true);
      }
    }, 
    enableSort: false, 
    pageSize: 20, 
    tableRendered: function() {
      this.updatePaginator();
      updateMemoryBreakpointsView();
    }
  });
  editableGrid.load({"metadata": metadata,  "data": data});
  editableGrid.renderGrid("memoryview",  "testgrid");
  addHoverMemoryView();

  $('#help_r').tooltipster({
    contentAsHTML: true,
    content: 'Lecture (read)',
    position: 'top'
  });
  $('#help_w').tooltipster({
    contentAsHTML: true,
    content: '&Eacute;criture (write)',
    position: 'top'
  });
  $('#help_rw').tooltipster({
    contentAsHTML: true,
    content: 'Lecture ou &eacute;criture (read/write)',
    position: 'top'
  });
  $('#help_e').tooltipster({
    contentAsHTML: true,
    content: 'Ex&eacute;cution (execute)',
    position: 'top'
  });
  $('#help_instr').tooltipster({
    contentAsHTML: true,
    content: 'Instruction courante',
    position: 'top'
  });
});