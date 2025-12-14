
$(document).ready(function() {
    // Pulse effect on buttons when clicked (only for index)
    $("#index-container .button").on("click", function() {
        $(this).css("transform", "scale(0.95)").css("transition", "transform 0.1s ease");
        setTimeout(() => {
            $(this).css("transform", "scale(1)");
        }, 100);
    });

    // Hover effect (only for index)
    $("#index-container .button").hover(
        function() {
            $(this).css("transform", "scale(1.1)");
        },
        function() {
            $(this).css("transform", "scale(1)");
        }
    );

    // Initialize alert sound
    var alertSound = new Audio('/static/alert.wav');

    // WebSocket connection
    var socket = io.connect('http://' + document.domain + ':' + location.port);

    socket.on('connect', function() {
        console.log('WebSocket connected');
    });

    socket.on('new_urgent_report', function(report) {
        // Check if report already exists to avoid duplicates
        if ($('#report-table tbody tr[data-report-id="' + report.report_id + '"]').length === 0) {
            var descriptionHtml = '<ul>' + report.description.map(sentence => '<li>' + sentence + '</li>').join('') + '</ul>';
            var newRow = `
                <tr class="urgent" data-report-id="${report.report_id}">
                    <td>${report.report_id}</td>
                    <td>${report.incident_date}</td>
                    <td>${report.location}</td>
                    <td>${report.incident_type}</td>
                    <td>${descriptionHtml}</td>
                    <td>${report.witness}</td>
                    <td>${report.submission_date}</td>
                    <td>${report.status}</td>
                    <td>${report.distress_percentage}%</td>
                </tr>
            `;
            $('#report-table tbody').prepend(newRow); // Add to top
            $('#urgent-message').text(`New Urgent Report Detected! ID: ${report.report_id}`);
            $('#urgent-popup').fadeIn(500);
            alertSound.play().catch(function() {
                console.log("Audio playback failed; ensure alert.wav is in static/");
            });
            $(".urgent").each(function(index) {
                $(this).delay(200 * index).fadeIn(600);
            });
        }
    });
});
