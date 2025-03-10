/**
 * Luxe Mattresses Chatbot JavaScript
 * Enhanced with debug logging, fixes, link handling, and dashboard integration
 */
jQuery(document).ready(function($) {
    'use strict';

    console.log('Luxe Chatbot: Script initialized');
    
    // Log the plugin parameters to verify they're properly passed
    console.log('Luxe Chatbot: Parameters loaded', luxe_chatbot_params);

    try {
        // Global variables
        let isOpen = false;
        let conversationHistory = [];
        let conversationId = getConversationId();

        // DOM elements
        const $container = $('#luxe-chatbot-container');
        const $toggle = $('#luxe-chatbot-toggle');
        const $widget = $('#luxe-chatbot-widget');
        const $close = $('.luxe-chatbot-close');
        const $messages = $('#luxe-chatbot-messages');
        const $input = $('#luxe-chatbot-input');
        const $send = $('#luxe-chatbot-send');
        const $typingIndicator = $('.luxe-chatbot-typing-indicator');

        // Check if elements exist on the page
        console.log('Luxe Chatbot: Container exists?', $container.length > 0);
        console.log('Luxe Chatbot: Toggle button exists?', $toggle.length > 0);
        console.log('Luxe Chatbot: Widget exists?', $widget.length > 0);
        console.log('Luxe Chatbot: Using conversation ID:', conversationId);

        // Initialize - force display for debugging
        $container.css('display', 'block');
        $toggle.css('display', 'flex');
        
        // Make sure typing indicator is hidden initially
        $typingIndicator.css('display', 'none');
        
        // Fix send button icon
        fixSendButtonIcon();
        
        // Log success
        console.log('Luxe Chatbot: Force displayed elements');

        // Bind events
        bindEvents();

        /**
         * Fix send button icon visibility
         */
        function fixSendButtonIcon() {
            $send.find('svg').css({
                'display': 'block',
                'visibility': 'visible',
                'fill': 'white',
                'stroke': 'white',
                'opacity': '1',
                'position': 'absolute',
                'top': '50%',
                'left': '50%',
                'transform': 'translate(-50%, -50%)'
            });
        }

        /**
         * Bind all event handlers
         */
        function bindEvents() {
            console.log('Luxe Chatbot: Binding events');
            
            // Toggle chatbot
            $toggle.on('click', function(e) {
                console.log('Luxe Chatbot: Toggle button clicked');
                toggleChatbot();
                e.preventDefault();
            });
            
            $close.on('click', function(e) {
                console.log('Luxe Chatbot: Close button clicked');
                closeChatbot();
                e.preventDefault();
            });

            // Send message
            $send.on('click', function(e) {
                console.log('Luxe Chatbot: Send button clicked');
                sendMessage();
                e.preventDefault();
            });
            
            $input.on('keypress', function(e) {
                if (e.which === 13) {
                    console.log('Luxe Chatbot: Enter key pressed in input');
                    sendMessage();
                    e.preventDefault();
                }
            });
            
            // Delegate click handler for links in messages
            $messages.on('click', 'a', function(e) {
                console.log('Luxe Chatbot: Link clicked:', $(this).attr('href'));
                // Allow links to open in new tab by default
                if (!$(this).attr('target')) {
                    $(this).attr('target', '_blank');
                }
            });
            
            console.log('Luxe Chatbot: Events bound successfully');
        }

        /**
         * Toggle chatbot visibility
         */
        function toggleChatbot() {
            if (isOpen) {
                closeChatbot();
            } else {
                openChatbot();
            }
        }

        /**
         * Open chatbot widget
         */
        function openChatbot() {
            console.log('Luxe Chatbot: Opening chatbot');
            $container.addClass('active');
            isOpen = true;
            scrollToBottom();
            $input.focus();
        }

        /**
         * Close chatbot widget
         */
        function closeChatbot() {
            console.log('Luxe Chatbot: Closing chatbot');
            $container.removeClass('active');
            isOpen = false;
        }

        /**
         * Generate or retrieve a unique conversation ID
         * This is used to track conversations in the dashboard
         */
        function getConversationId() {
            let id = localStorage.getItem('luxe_chatbot_conversation_id');
            
            // If no ID exists or it's older than 2 hours, create a new one
            const twoHoursAgo = new Date();
            twoHoursAgo.setHours(twoHoursAgo.getHours() - 2);
            
            const lastActivity = localStorage.getItem('luxe_chatbot_last_activity');
            const needsNewSession = !lastActivity || new Date(lastActivity) < twoHoursAgo;
            
            if (!id || needsNewSession) {
                // Generate a random ID with timestamp for uniqueness
                id = 'conv_' + Math.random().toString(36).substr(2, 9) + '_' + Date.now();
                localStorage.setItem('luxe_chatbot_conversation_id', id);
                console.log('Luxe Chatbot: Created new conversation ID:', id);
            }
            
            // Update last activity timestamp
            localStorage.setItem('luxe_chatbot_last_activity', new Date().toISOString());
            
            return id;
        }

        /**
         * Send message to API and handle response
         */
        function sendMessage() {
            const message = $input.val().trim();
            
            if (!message) {
                console.log('Luxe Chatbot: Empty message, not sending');
                return;
            }

            console.log('Luxe Chatbot: Sending message:', message);

            // Add user message to chat
            addMessage(message, 'user');

            // Log user message to dashboard
            logConversation(message, 'user');

            // Clear input
            $input.val('');

            // Show typing indicator - make sure it's displayed
            $typingIndicator.css('display', 'flex');
            scrollToBottom();

            // Prepare AJAX request to the API
            console.log('Luxe Chatbot: Making request to API:', luxe_chatbot_params.api_url + '/api/query');
            
            // Make API request
            $.ajax({
                url: luxe_chatbot_params.api_url + '/api/query',
                type: 'POST',
                contentType: 'application/json',
                data: JSON.stringify({
                    query: message
                }),
                success: function(response) {
                    console.log('Luxe Chatbot: API response received:', response);
                    
                    // Hide typing indicator - explicitly set display to none
                    $typingIndicator.css('display', 'none');

                    // Add bot response to chat
                    if (response && response.response) {
                        addMessage(response.response, 'bot');
                        
                        // Log bot message to dashboard
                        logConversation(response.response, 'bot');
                    } else {
                        console.log('Luxe Chatbot: Invalid response format:', response);
                        const errorMsg = "I'm sorry, I couldn't process your request.";
                        addMessage(errorMsg, 'bot');
                        
                        // Log error message to dashboard
                        logConversation(errorMsg, 'bot');
                    }
                    
                    // Store conversation in history
                    saveConversation(message, response.response || "I'm sorry, I couldn't process your request.");
                    
                    // Scroll to bottom
                    scrollToBottom();
                    
                    // Update last activity timestamp
                    localStorage.setItem('luxe_chatbot_last_activity', new Date().toISOString());
                },
                error: function(xhr, status, error) {
                    console.error('Luxe Chatbot: API Error:', { status, error, responseText: xhr.responseText });
                    
                    // Hide typing indicator - explicitly set display to none
                    $typingIndicator.css('display', 'none');
                    
                    // Add error message
                    const errorMsg = "I'm sorry, there was an error connecting to the server. Please try again later.";
                    addMessage(errorMsg, 'bot');
                    
                    // Log error message to dashboard
                    logConversation(errorMsg, 'bot');
                    
                    // Scroll to bottom
                    scrollToBottom();
                }
            });
        }

        /**
         * Log conversation to the dashboard database
         */
        function logConversation(message, type) {
            // Check if REST API parameters are available
            if (!luxe_chatbot_params.rest_url) {
                console.log('Luxe Chatbot: REST URL not defined, skipping dashboard logging');
                return;
            }
            
            console.log('Luxe Chatbot: Logging message to dashboard:', type);
            
            // Make AJAX request to log the conversation
            $.ajax({
                url: luxe_chatbot_params.rest_url + 'log',
                type: 'POST',
                contentType: 'application/json',
                data: JSON.stringify({
                    conversation_id: conversationId,
                    message_content: message,
                    message_type: type,
                    page_url: window.location.href
                }),
                beforeSend: function(xhr) {
                    xhr.setRequestHeader('X-WP-Nonce', luxe_chatbot_params.rest_nonce);
                },
                success: function(response) {
                    console.log('Luxe Chatbot: Message logged to dashboard successfully');
                },
                error: function(xhr, status, error) {
                    console.error('Luxe Chatbot: Error logging message to dashboard:', error);
                }
            });
        }

        /**
         * Add message to chat interface
         */
        function addMessage(message, type) {
            console.log('Luxe Chatbot: Adding message type:', type, 'Content:', message);
            
            const isBot = type === 'bot';
            
            // Process message content to make links clickable
            const processedMessage = makeLinksClickable(message);
            
            // Create message HTML
            const html = `
                <div class="luxe-chatbot-message ${isBot ? 'bot-message' : 'user-message'}">
                    <div class="luxe-chatbot-avatar">
                        ${isBot ? 
                        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><circle cx="12" cy="10" r="4"></circle><line x1="12" y1="14" x2="12" y2="18"></line><line x1="8" y1="22" x2="16" y2="22"></line></svg>' : 
                        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path><circle cx="12" cy="7" r="4"></circle></svg>'}
                    </div>
                    <div class="luxe-chatbot-message-content">
                        ${processedMessage}
                    </div>
                </div>
            `;
            
            // Append message
            $messages.append(html);
            
            // Scroll to bottom
            scrollToBottom();
        }
        
        /**
         * Make links in text clickable
         */
        function makeLinksClickable(text) {
            // URL pattern: matches URLs starting with http://, https://, or www.
            const urlPattern = /(\b(https?|ftp):\/\/[-A-Z0-9+&@#\/%?=~_|!:,.;]*[-A-Z0-9+&@#\/%=~_|])/gim;
            // www pattern: matches strings starting with www. not preceded by http:// or https://
            const wwwPattern = /(^|[^\/])(www\.[\S]+(\b|$))/gim;
            // Email pattern: matches email addresses
            const emailPattern = /(([a-zA-Z0-9\-\_\.])+@[a-zA-Z\_]+?(\.[a-zA-Z]{2,6})+)/gim;
            
            // Replace URLs
            let processedText = text.replace(urlPattern, '<a href="$1" target="_blank" rel="noopener noreferrer">$1</a>');
            
            // Replace www. URLs (not preceded by http:// or https://)
            processedText = processedText.replace(wwwPattern, '$1<a href="http://$2" target="_blank" rel="noopener noreferrer">$2</a>');
            
            // Replace email addresses
            processedText = processedText.replace(emailPattern, '<a href="mailto:$1">$1</a>');
            
            return processedText;
        }

        /**
         * Show typing indicator
         */
        function showTypingIndicator() {
            console.log('Luxe Chatbot: Showing typing indicator');
            $typingIndicator.css('display', 'flex'); // Use CSS directly to ensure display
            scrollToBottom();
        }

        /**
         * Hide typing indicator
         */
        function hideTypingIndicator() {
            console.log('Luxe Chatbot: Hiding typing indicator');
            $typingIndicator.css('display', 'none'); // Use CSS directly to ensure it's hidden
        }

        /**
         * Scroll messages container to bottom
         */
        function scrollToBottom() {
            $messages.scrollTop($messages[0].scrollHeight);
        }
        
        /**
         * Save conversation to localStorage
         */
        function saveConversation(userMessage, botResponse) {
            // Add to history array
            conversationHistory.push({
                user: userMessage,
                bot: botResponse,
                timestamp: new Date().toISOString()
            });
            
            // Limit history to last 50 messages
            if (conversationHistory.length > 50) {
                conversationHistory = conversationHistory.slice(-50);
            }
            
            // Store in localStorage
            try {
                localStorage.setItem('luxe_chatbot_conversation', JSON.stringify(conversationHistory));
                console.log('Luxe Chatbot: Conversation saved to localStorage');
            } catch (e) {
                console.error('Luxe Chatbot: Error saving conversation:', e);
            }
        }
        
        /**
         * Add debug functionality (only in debug mode)
         */
        if (luxe_chatbot_params.debug) {
            console.log('Luxe Chatbot: Adding debug elements');
            
            // Add to page
            $('body').append('<div id="luxe-chatbot-debug" style="position:fixed; top:10px; right:10px; background:rgba(0,0,0,0.7); color:white; padding:10px; z-index:999999; font-size:12px;">Luxe Chatbot Debug</div>');
            
            // Add click handler
            $('#luxe-chatbot-debug').on('click', function() {
                console.log('Luxe Chatbot: Debug panel clicked');
                
                // Check elements
                console.log('Container:', $container.length, $container);
                console.log('Toggle:', $toggle.length, $toggle);
                console.log('Widget:', $widget.length, $widget);
                console.log('Conversation ID:', conversationId);
                console.log('REST URL:', luxe_chatbot_params.rest_url);
                console.log('Site URL:', luxe_chatbot_params.site_url);
                
                // Toggle visibility for debugging
                $container.css('display', 'block');
                $toggle.css('display', 'flex');
                
                // Force open
                openChatbot();
                
                // Test message with link
                addMessage('This is a test message with a link: Check out <a href="https://luxemattresses.com" target="_blank">Luxe Mattresses</a> or visit www.luxemattresses.com or contact support@luxemattresses.com', 'bot');
                
                // Fix send button icon again
                fixSendButtonIcon();
                
                // Test dashboard logging
                if (luxe_chatbot_params.rest_url) {
                    logConversation('This is a test message from the debug panel', 'bot');
                }
                
                alert('Luxe Chatbot debug info logged to console. Chatbot forced visible.');
            });
        }
    } catch (e) {
        console.error('Luxe Chatbot: Critical error in initialization:', e);
    }
});