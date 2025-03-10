<?php
/**
 * Plugin Name: Luxe Customer Support Chatbot
 * Plugin URI: https://github.com/TERRA26/chatbot
 * Description: A smart, context-aware chatbot for Luxe Mattresses that helps customers find the perfect mattress.
 * Version: 1.0.2
 * Author: Your Name
 * Author URI: https://github.com/TERRA26
 * Text Domain: luxe-chatbot
 */

// If this file is called directly, abort.
if (!defined('WPINC')) {
    die;
}

// Define plugin constants
define('LUXE_CHATBOT_VERSION', '1.0.2');
define('LUXE_CHATBOT_PLUGIN_DIR', plugin_dir_path(__FILE__));
define('LUXE_CHATBOT_PLUGIN_URL', plugin_dir_url(__FILE__));
define('LUXE_CHATBOT_API_URL', 'https://web-production-b947.up.railway.app');

// Include the dashboard class
require_once LUXE_CHATBOT_PLUGIN_DIR . 'includes/luxe-chatbot-dashboard.php';

class Luxe_Chatbot {

    /**
     * Constructor
     */
    public function __construct() {
        // Enqueue scripts and styles
        add_action('wp_enqueue_scripts', array($this, 'enqueue_scripts'));
        
        // Add chatbot HTML to footer
        add_action('wp_footer', array($this, 'add_chatbot_html'));
        
        // Add admin menu
        add_action('admin_menu', array($this, 'add_admin_menu'));
        
        // Register settings
        add_action('admin_init', array($this, 'register_settings'));
        
        // Add init action to log when plugin is loaded
        add_action('init', array($this, 'log_plugin_init'));
    }
    
    /**
     * Log when plugin is initialized
     */
    public function log_plugin_init() {
        // This action helps verify the plugin is properly loaded in WordPress
        error_log('Luxe Chatbot Plugin: Initialized');
    }

    /**
     * Enqueue scripts and styles
     */
    public function enqueue_scripts() {
        // Log that we're trying to enqueue scripts
        error_log('Luxe Chatbot Plugin: Enqueuing scripts and styles');
        
        // Enqueue CSS
        wp_enqueue_style(
            'luxe-chatbot-style',
            LUXE_CHATBOT_PLUGIN_URL . 'chatbot.css',
            array(),
            LUXE_CHATBOT_VERSION
        );

        // Enqueue JavaScript
        wp_enqueue_script(
            'luxe-chatbot-script',
            LUXE_CHATBOT_PLUGIN_URL . 'chatbot.js',
            array('jquery'),
            LUXE_CHATBOT_VERSION,
            true
        );

        // Localize script with data
        wp_localize_script(
            'luxe-chatbot-script',
            'luxe_chatbot_params',
            array(
                'api_url' => LUXE_CHATBOT_API_URL,
                'debug' => true, // Enable debug mode for console logging
                'plugin_url' => LUXE_CHATBOT_PLUGIN_URL,
                'site_url' => site_url(),
                'rest_nonce' => wp_create_nonce('wp_rest'),
                'rest_url' => rest_url('luxe-chatbot/v1/')
            )
        );
    }

    /**
     * Process message text for safe HTML output with links
     * 
     * @param string $message Message text to process
     * @return string Processed message with safe HTML and clickable links
     */
    public function process_message_text($message) {
        // First sanitize the message
        $message = wp_kses_post($message);
        
        // Process URLs
        $url_pattern = '/(\b(https?|ftp):\/\/[-A-Z0-9+&@#\/%?=~_|!:,.;]*[-A-Z0-9+&@#\/%=~_|])/im';
        $message = preg_replace($url_pattern, '<a href="$1" target="_blank" rel="noopener noreferrer">$1</a>', $message);
        
        // Process www URLs
        $www_pattern = '/(^|[^\/])(www\.[\S]+(\b|$))/im';
        $message = preg_replace($www_pattern, '$1<a href="http://$2" target="_blank" rel="noopener noreferrer">$2</a>', $message);
        
        // Process email addresses
        $email_pattern = '/(([a-zA-Z0-9\-\_\.])+@[a-zA-Z\_]+?(\.[a-zA-Z]{2,6})+)/im';
        $message = preg_replace($email_pattern, '<a href="mailto:$1">$1</a>', $message);
        
        return $message;
    }

    /**
     * Add chatbot HTML to the footer
     */
    public function add_chatbot_html() {
        // Log that we're trying to add the chatbot HTML
        error_log('Luxe Chatbot Plugin: Adding chatbot HTML to footer');
        
        // Get settings
        $welcome_message = get_option('luxe_chatbot_welcome_message', 'Welcome to Luxe Mattresses! How can I help you find the perfect mattress today?');
        $chatbot_name = get_option('luxe_chatbot_chatbot_name', 'Luxe Support');
        $position = get_option('luxe_chatbot_position', 'right');
        $primary_color = get_option('luxe_chatbot_color_primary', '#0077b6'); // Updated default to darker blue
        $secondary_color = get_option('luxe_chatbot_color_secondary', '#FFFFFF');

        // Build position class
        $position_class = 'chatbot-' . $position;
        ?>
        <div id="luxe-chatbot-container" class="luxe-chatbot-container <?php echo esc_attr($position_class); ?>">
            <!-- Chatbot toggle button -->
            <div id="luxe-chatbot-toggle" class="luxe-chatbot-toggle">
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="28" height="28" fill="white" stroke="white" stroke-width="1">
                    <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
                </svg>
            </div>

            <!-- Chatbot widget -->
            <div id="luxe-chatbot-widget" class="luxe-chatbot-widget">
                <!-- Chatbot header -->
                <div class="luxe-chatbot-header">
                    <div class="luxe-chatbot-title"><?php echo esc_html($chatbot_name); ?></div>
                    <div class="luxe-chatbot-close">
                        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <line x1="18" y1="6" x2="6" y2="18"></line>
                            <line x1="6" y1="6" x2="18" y2="18"></line>
                        </svg>
                    </div>
                </div>

                <!-- Chatbot messages container -->
                <div id="luxe-chatbot-messages" class="luxe-chatbot-messages">
                    <!-- Welcome message -->
                    <div class="luxe-chatbot-message bot-message">
                        <div class="luxe-chatbot-avatar">
                            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" fill="white" stroke="white" stroke-width="1">
                                <circle cx="12" cy="12" r="10"></circle>
                                <circle cx="12" cy="10" r="4"></circle>
                                <line x1="12" y1="14" x2="12" y2="18"></line>
                                <line x1="8" y1="22" x2="16" y2="22"></line>
                            </svg>
                        </div>
                        <div class="luxe-chatbot-message-content">
                            <?php echo $this->process_message_text($welcome_message); ?>
                        </div>
                    </div>

                    <!-- Typing indicator (hidden by default) -->
                    <div class="luxe-chatbot-typing-indicator" style="display: none;">
                        <div class="luxe-chatbot-dot"></div>
                        <div class="luxe-chatbot-dot"></div>
                        <div class="luxe-chatbot-dot"></div>
                    </div>
                </div>

                <!-- Chatbot input container -->
                <div class="luxe-chatbot-input-container">
                    <input type="text" id="luxe-chatbot-input" class="luxe-chatbot-input" placeholder="Ask about our mattresses...">
                    <button id="luxe-chatbot-send" class="luxe-chatbot-send">
                        <!-- Fixed paper plane SVG icon -->
                        <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="white" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <path d="M22 2L11 13"></path>
                            <path d="M22 2L15 22L11 13L2 9L22 2Z"></path>
                        </svg>
                    </button>
                </div>

                <!-- Chatbot footer -->
                <div class="luxe-chatbot-footer">
                    <span>Powered by Luxe Mattresses</span>
                </div>
            </div>
        </div>

        <!-- Apply custom colors - Important override styles -->
        <style>
            /* Base styles */
            .luxe-chatbot-toggle {
                background-color: <?php echo esc_attr($primary_color); ?> !important;
                color: <?php echo esc_attr($secondary_color); ?> !important;
            }
            
            .luxe-chatbot-header {
                background-color: <?php echo esc_attr($primary_color); ?> !important;
                color: <?php echo esc_attr($secondary_color); ?> !important;
            }
            
            .luxe-chatbot-send {
                background-color: <?php echo esc_attr($primary_color); ?> !important;
                color: <?php echo esc_attr($secondary_color); ?> !important;
                position: relative !important;
            }
            
            .bot-message .luxe-chatbot-message-content {
                background-color: <?php echo esc_attr($primary_color); ?> !important;
                color: <?php echo esc_attr($secondary_color); ?> !important;
            }
            
            .bot-message .luxe-chatbot-message-content:before {
                background-color: <?php echo esc_attr($primary_color); ?> !important;
            }
            
            .bot-message .luxe-chatbot-avatar {
                background-color: <?php echo esc_attr($primary_color); ?> !important;
                color: <?php echo esc_attr($secondary_color); ?> !important;
            }
            
            .luxe-chatbot-typing-indicator .luxe-chatbot-dot {
                background-color: <?php echo esc_attr($primary_color); ?> !important;
            }
            
            /* Fix SVG icons */
            .luxe-chatbot-send svg {
                fill: <?php echo esc_attr($secondary_color); ?> !important;
                stroke: <?php echo esc_attr($secondary_color); ?> !important;
                position: absolute !important;
                top: 50% !important;
                left: 50% !important;
                transform: translate(-50%, -50%) !important;
                display: block !important;
                visibility: visible !important;
                opacity: 1 !important;
                pointer-events: none !important;
            }
            
            /* Force display for debugging */
            .luxe-chatbot-container {
                display: block !important;
                z-index: 999999 !important;
            }
            
            /* Link styles */
            .luxe-chatbot-message-content a {
                color: inherit !important;
                text-decoration: underline !important;
                font-weight: 500 !important;
                transition: opacity 0.2s ease !important;
            }
            
            .bot-message .luxe-chatbot-message-content a {
                color: white !important;
                text-decoration-color: rgba(255, 255, 255, 0.7) !important;
            }
            
            .user-message .luxe-chatbot-message-content a {
                color: #0077b6 !important;
                text-decoration-color: rgba(0, 119, 182, 0.5) !important;
            }
        </style>

        <!-- Console debug message to verify HTML is added -->
        <script>
            console.log('Luxe Chatbot: HTML added to page');
            
            // Ensure the send button icon is visible on page load
            jQuery(document).ready(function($) {
                $('#luxe-chatbot-send svg').css({
                    'display': 'block',
                    'visibility': 'visible',
                    'fill': '<?php echo esc_attr($secondary_color); ?>',
                    'stroke': '<?php echo esc_attr($secondary_color); ?>',
                    'opacity': '1'
                });
            });
        </script>
        <?php
    }

    /**
     * Add admin menu
     */
    public function add_admin_menu() {
        add_options_page(
            'Luxe Chatbot Settings',
            'Luxe Chatbot',
            'manage_options',
            'luxe-chatbot-settings',
            array($this, 'render_admin_page')
        );
    }

    /**
     * Register settings
     */
    public function register_settings() {
        register_setting('luxe-chatbot-settings-group', 'luxe_chatbot_welcome_message');
        register_setting('luxe-chatbot-settings-group', 'luxe_chatbot_color_primary');
        register_setting('luxe-chatbot-settings-group', 'luxe_chatbot_color_secondary');
        register_setting('luxe-chatbot-settings-group', 'luxe_chatbot_chatbot_name');
        register_setting('luxe-chatbot-settings-group', 'luxe_chatbot_position');
    }

    /**
     * Render admin page
     */
    public function render_admin_page() {
        // Get saved options
        $welcome_message = get_option('luxe_chatbot_welcome_message', 'Welcome to Luxe Mattresses! How can I help you find the perfect mattress today?');
        $chatbot_name = get_option('luxe_chatbot_chatbot_name', 'Luxe Support');
        $position = get_option('luxe_chatbot_position', 'right');
        $primary_color = get_option('luxe_chatbot_color_primary', '#0077b6');
        $secondary_color = get_option('luxe_chatbot_color_secondary', '#FFFFFF');
        
        // Get dashboard URL
        $access_key = get_option('luxe_chatbot_dashboard_key', '');
        $dashboard_url = '';
        if (!empty($access_key)) {
            $dashboard_url = home_url('chatbot-dashboard/' . $access_key);
        }
        ?>
        <div class="wrap">
            <h1>Luxe Mattresses Chatbot Settings</h1>
            
            <?php if (!empty($dashboard_url)) : ?>
            <div class="notice notice-success">
                <p><strong>Statistics Dashboard:</strong> View your chatbot stats at <a href="<?php echo esc_url($dashboard_url); ?>" target="_blank"><?php echo esc_html($dashboard_url); ?></a></p>
                <p>You can also access the dashboard from the admin menu under "Chatbot Stats".</p>
            </div>
            <?php endif; ?>
            
            <form method="post" action="options.php">
                <?php settings_fields('luxe-chatbot-settings-group'); ?>
                
                <table class="form-table">
                    <tr>
                        <th scope="row">Chatbot Name</th>
                        <td>
                            <input type="text" name="luxe_chatbot_chatbot_name" value="<?php echo esc_attr($chatbot_name); ?>" class="regular-text">
                        </td>
                    </tr>
                    
                    <tr>
                        <th scope="row">Welcome Message</th>
                        <td>
                            <textarea name="luxe_chatbot_welcome_message" rows="3" class="large-text"><?php echo esc_textarea($welcome_message); ?></textarea>
                            <p class="description">You can include links using standard http:// or www. format. They will be automatically made clickable.</p>
                        </td>
                    </tr>
                    
                    <tr>
                        <th scope="row">Position</th>
                        <td>
                            <select name="luxe_chatbot_position">
                                <option value="right" <?php selected($position, 'right'); ?>>Bottom Right</option>
                                <option value="left" <?php selected($position, 'left'); ?>>Bottom Left</option>
                            </select>
                        </td>
                    </tr>
                    
                    <tr>
                        <th scope="row">Primary Color</th>
                        <td>
                            <input type="color" name="luxe_chatbot_color_primary" value="<?php echo esc_attr($primary_color); ?>">
                            <p class="description">Used for chatbot header, button and bot messages</p>
                        </td>
                    </tr>
                    
                    <tr>
                        <th scope="row">Secondary Color</th>
                        <td>
                            <input type="color" name="luxe_chatbot_color_secondary" value="<?php echo esc_attr($secondary_color); ?>">
                            <p class="description">Used for text color on primary color backgrounds</p>
                        </td>
                    </tr>
                </table>
                
                <?php submit_button(); ?>
            </form>
            
            <div class="notice notice-info">
                <p><strong>Troubleshooting:</strong></p>
                <p>If the chatbot is not showing on your site, please check:</p>
                <ol>
                    <li>Your theme's <code>footer.php</code> includes <code>wp_footer()</code> function call</li>
                    <li>JavaScript console for any errors</li>
                    <li>Check that the API endpoint is working by visiting <a href="<?php echo esc_url(LUXE_CHATBOT_API_URL . '/health'); ?>" target="_blank"><?php echo esc_html(LUXE_CHATBOT_API_URL . '/health'); ?></a></li>
                </ol>
                <p>For more help, check the browser console to see detailed logs.</p>
            </div>
        </div>
        <?php
    }
}

// Initialize the plugin
$luxe_chatbot = new Luxe_Chatbot();

// Initialize the dashboard
$luxe_chatbot_dashboard = new Luxe_Chatbot_Dashboard();

// Add activation hook to write to log when plugin is activated
register_activation_hook(__FILE__, 'luxe_chatbot_activation');
function luxe_chatbot_activation() {
    error_log('Luxe Chatbot Plugin: Activated');
    
    // Create database tables for the dashboard
    global $luxe_chatbot_dashboard;
    if (method_exists($luxe_chatbot_dashboard, 'maybe_create_tables')) {
        $luxe_chatbot_dashboard->maybe_create_tables();
    }
}

// Add deactivation hook
register_deactivation_hook(__FILE__, 'luxe_chatbot_deactivation');
function luxe_chatbot_deactivation() {
    error_log('Luxe Chatbot Plugin: Deactivated');
}