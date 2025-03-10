/**
 * Luxe Chatbot Dashboard JavaScript
 */
(function($) {
    'use strict';
    
    // Chart instance
    let conversationsChart = null;
    
    // Initialize dashboard
    window.initDashboard = function(dashboardData) {
        // Load all data on page load
        loadAllData();
        
        // Set up refresh button
        $('#refresh-stats').on('click', function() {
            loadAllData();
            $(this).addClass('loading').prop('disabled', true);
            setTimeout(() => {
                $(this).removeClass('loading').prop('disabled', false);
            }, 1000);
        });
        
        // Set up copy URL button
        $('.copy-url').on('click', function() {
            const urlInput = $(this).prev('.share-url');
            urlInput.select();
            document.execCommand('copy');
            
            // Show copied message
            const originalText = $(this).text();
            $(this).text('Copied!');
            setTimeout(() => {
                $(this).text(originalText);
            }, 2000);
        });
        
        // Load all data from API
        function loadAllData() {
            fetchStats();
            fetchCommonQueries();
            fetchRecentConversations();
        }
        
        // Fetch stats from API
        function fetchStats() {
            $.ajax({
                url: dashboardData.api_url + 'stats',
                method: 'GET',
                beforeSend: function(xhr) {
                    xhr.setRequestHeader('X-WP-Nonce', dashboardData.nonce);
                },
                success: function(response) {
                    updateStatCards(response);
                    updateConversationsChart(response.daily_stats);
                    $('#last-updated').text(formatDateTime(response.last_updated));
                },
                error: function(xhr) {
                    console.error('Error fetching stats:', xhr.responseText);
                }
            });
        }
        
        // Fetch common queries
        function fetchCommonQueries() {
            $.ajax({
                url: dashboardData.api_url + 'common-queries',
                method: 'GET',
                beforeSend: function(xhr) {
                    xhr.setRequestHeader('X-WP-Nonce', dashboardData.nonce);
                },
                success: function(response) {
                    renderCommonQueries(response);
                },
                error: function(xhr) {
                    console.error('Error fetching common queries:', xhr.responseText);
                    $('#common-queries').html('<p>Error loading data.</p>');
                }
            });
        }
        
        // Fetch recent conversations
        function fetchRecentConversations() {
            // Skip for public dashboard
            if (dashboardData.is_public) {
                return;
            }
            
            $.ajax({
                url: dashboardData.api_url + 'conversations',
                method: 'GET',
                beforeSend: function(xhr) {
                    xhr.setRequestHeader('X-WP-Nonce', dashboardData.nonce);
                },
                success: function(response) {
                    renderRecentConversations(response);
                },
                error: function(xhr) {
                    console.error('Error fetching conversations:', xhr.responseText);
                    $('#recent-conversations').html('<p>Error loading data.</p>');
                }
            });
        }
        
        // Update stat cards with data
        function updateStatCards(stats) {
            $('#total-conversations .stat-value').text(stats.total_conversations.toLocaleString());
            $('#avg-messages .stat-value').text(stats.avg_messages_per_conversation);
            
            // Calculate today's conversations
            const today = new Date().toISOString().split('T')[0];
            let todayConversations = 0;
            
            if (stats.daily_stats && stats.daily_stats.length > 0) {
                const todayStat = stats.daily_stats.find(item => item.date.includes(today));
                if (todayStat) {
                    todayConversations = todayStat.count;
                }
            }
            
            $('#today-conversations .stat-value').text(todayConversations.toLocaleString());
        }
        
        // Update conversations chart
        function updateConversationsChart(dailyStats) {
            const labels = [];
            const data = [];
            
            if (dailyStats && dailyStats.length > 0) {
                dailyStats.forEach(item => {
                    // Format date to just MM/DD
                    const date = new Date(item.date);
                    const formattedDate = (date.getMonth() + 1) + '/' + date.getDate();
                    
                    labels.push(formattedDate);
                    data.push(item.count);
                });
            }
            
            const ctx = document.getElementById('conversations-chart').getContext('2d');
            
            // Destroy existing chart if exists
            if (conversationsChart) {
                conversationsChart.destroy();
            }
            
            // Create new chart
            conversationsChart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: labels,
                    datasets: [{
                        label: 'Conversations',
                        data: data,
                        fill: true,
                        backgroundColor: 'rgba(0, 119, 182, 0.1)',
                        borderColor: 'rgba(0, 119, 182, 1)',
                        tension: 0.4,
                        pointBackgroundColor: 'rgba(0, 119, 182, 1)',
                        pointRadius: 4,
                        pointHoverRadius: 6
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            display: false
                        },
                        tooltip: {
                            mode: 'index',
                            intersect: false,
                            callbacks: {
                                label: function(context) {
                                    return context.parsed.y + ' conversations';
                                }
                            }
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            ticks: {
                                precision: 0
                            }
                        }
                    }
                }
            });
        }
        
        // Render common queries
        function renderCommonQueries(queries) {
            if (!queries || queries.length === 0) {
                $('#common-queries').html('<p>No common queries found.</p>');
                return;
            }
            
            let html = '<ul class="query-list">';
            
            queries.forEach(query => {
                html += `
                    <li>
                        <span class="query-text">${escapeHtml(query.message_content)}</span>
                        <span class="query-count">${query.frequency} times</span>
                    </li>
                `;
            });
            
            html += '</ul>';
            
            $('#common-queries').html(html);
        }
        
        // Render recent conversations
        function renderRecentConversations(conversations) {
            if (!conversations || conversations.length === 0) {
                $('#recent-conversations').html('<p>No conversations found.</p>');
                return;
            }
            
            let html = '<div class="conversation-list">';
            
            conversations.forEach(conversation => {
                const formattedDate = formatDateTime(conversation.created_at);
                
                html += `
                    <div class="conversation-item">
                        <div class="conversation-header">
                            <span class="conversation-date">${formattedDate}</span>
                            <span class="conversation-count">${conversation.message_count} messages</span>
                        </div>
                        <div class="conversation-content">
                            <p class="first-message">${escapeHtml(conversation.first_message)}</p>
                        </div>
                    </div>
                `;
            });
            
            html += '</div>';
            
            $('#recent-conversations').html(html);
        }
        
        // Helper functions
        function formatDateTime(dateString) {
            const date = new Date(dateString);
            return date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
        }
        
        function escapeHtml(text) {
            if (!text) return '';
            
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }
    };
    
})(jQuery);