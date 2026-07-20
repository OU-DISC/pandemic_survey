const stats = (function () {
    return {

        updateStats: function () {
            var statsDiv = $('#stats');
            if (statsDiv.children().length > 0) {
                statsDiv.empty();
                statsDiv.tooltipster('destroy');
            }

            var total = Object.keys(bib.entries).length;
            var n = bib.nEntries;
            var s;
            if (n === 0) {
                s = 'Showing 0 of ' + total + ' publications';
            } else if (n === total) {
                s = 'Showing all ' + total + ' publications';
            } else if (n === 1) {
                s = 'Showing 1 of ' + total + ' publications';
            } else {
                s = 'Showing ' + n + ' of ' + total + ' publications';
            }
            statsDiv.append($('<span>', {
                class: 'stats-count',
                text: s
            }));

            var similarities = [];
            for (var i = 0; i < selectors.nSelectors; i++) {
                similarities.push(0)
            }
            $.each(bib.filteredEntries, function (id) {
                $.each(bib.entrySelectorSimilarities[id], function (i, similarity) {
                    similarities[i] += similarity;
                });
            });
            $.each(similarities, function (i, similarity) {
                if (similarity) {
                    similarities[i] = similarity / Math.max(bib.nEntries, 1);
                }
            });
            var sparklineDiv = $("<div>", {
                class: "vis sparkline"
            }).appendTo(statsDiv);
            selectors.vis(sparklineDiv, similarities);
            var tooltipDiv = $('<div>');
            $('<h3><span class="label">literature collection: </span>' + s + '</h3>').appendTo(tooltipDiv);
            var totalSimilarity = selectors.computeTotalSimilarity(similarities);
            if (selectors.getNActiveSelectors() > 0) {
                $('<div><span class="label">selector agreement: </span>' + totalSimilarity.toFixed(2) + '</div>').appendTo(tooltipDiv);
                if (totalSimilarity > 0) {
                    var visDiv = $('<div>', {
                        class: 'vis'
                    }).appendTo(tooltipDiv);
                    selectors.vis(visDiv, similarities);
                }
            }
            statsDiv.tooltipster({
                content: tooltipDiv,
                theme: 'tooltipster-survis'
            });
        }
    }
})();