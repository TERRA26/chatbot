<?php
/**
 * Luxe Chatbot Dashboard
 * 
 * This file provides a dashboard interface to view chatbot conversation statistics
 */

// If this file is called directly, abort.
if (!defined('WPINC')) {
    die;
}

class Luxe_Chatbot_Dashboard {
    
    /**
     * Constructor
     */
    public function __construct() {
        // Add admin menu
        add_action('admin_menu', array($this, 'add_dashboard_menu'));
        
        // Register REST API endpoints
        add_action('rest_api_init', array($this, 'register_rest_routes'));
        
        // Enqueue scripts and styles
        add_action('admin_enqueue_scripts', array($this, 'enqueue_dashboard_scripts'));
        
        // Add custom endpoint for public dashboard
        add_action('init', array($this, 'register_public_endpoint'));
    }
    
    /**
     * Add dashboard to admin menu
     */
    public function add_dashboard_menu() {
        add_menu_page(
            'Luxe Chatbot Dashboard',
            'Chatbot Stats',
            'manage_options',
            'luxe-chatbot-dashboard',
            array($this, 'render_dashboard_page'),
            'dashicons-chart-area',
            30
        );
    }
    
    /**
     * Register REST API routes for AJAX data fetching
     */
    public function register_rest_routes() {
        register_rest_route('luxe-chatbot/v1', '/stats', array(
            'methods' => 'GET',
            'callback' => array($this, 'get_conversation_stats'),
            'permission_callback' => function () {
                return current_user_can('manage_options');
            }
        ));
        
        register_rest_route('luxe-chatbot/v1', '/conversations', array(
            'methods' => 'GET',
            'callback' => array($this, 'get_recent_conversations'),
            'permission_callback' => function () {
                return current_user_can('manage_options');
            }
        ));
        
        register_rest_route('luxe-chatbot/v1', '/common-queries', array(
            'methods' => 'GET',
            'callback' => array($this, 'get_common_queries'),
            'permission_callback' => function () {
                return current_user_can('manage_options');
            }
        ));
    }
    
    /**
     * Register public endpoint for sharing dashboard
     */
    public function register_public_endpoint() {
        add_rewrite_rule(
            '^chatbot-dashboard/([^/]*)/?',
            'index.php?chatbot_dashboard=1&access_key=$matches[1]',
            'top'
        );
        
        add_filter('query_vars', function($query_vars) {
            $query_vars[] = 'chatbot_dashboard';
            $query_vars[] = 'access_key';
            return $query_vars;
        });
        
        add_action('template_redirect', function() {
            if (get_query_var('chatbot_dashboard')) {
                $access_key = get_query_var('access_key');
                $valid_key = get_option('luxe_chatbot_dashboard_key', '');
                
                if ($access_key === $valid_key) {
                    $this->render_public_dashboard();
                    exit;
                } else {
                    wp_die('Invalid access key for chatbot dashboard.');
                }
            }
        });
    }
    
    /**
     * Enqueue dashboard scripts and styles
     */
    public function enqueue_dashboard_scripts($hook) {
        if ('toplevel_page_luxe-chatbot-dashboard' !== $hook) {
            return;
        }
        
        wp_enqueue_style(
            'luxe-chatbot-dashboard-style',
            LUXE_CHATBOT_PLUGIN_URL . 'dashboard.css',
            array(),
            LUXE_CHATBOT_VERSION
        );
        
        wp_enqueue_script(
            'chart-js',
            'https://cdn.jsdelivr.net/npm/chart.js@3.7.1/dist/chart.min.js',
            array(),
            '3.7.1',
            true
        );
        
        wp_enqueue_script(
            'luxe-chatbot-dashboard-script',
            LUXE_CHATBOT_PLUGIN_URL . 'dashboard.js',
            array('jquery', 'chart-js'),
            LUXE_CHATBOT_VERSION,
            true
        );
        
        wp_localize_script(
            'luxe-chatbot-dashboard-script',
            'luxe_chatbot_dashboard',
            array(
                'api_url' => rest_url('luxe-chatbot/v1/'),
                'nonce' => wp_create_nonce('wp_rest'),
                'site_url' => site_url(),
                'public_url' => home_url('chatbot-dashboard/' . get_option('luxe_chatbot_dashboard_key', '')),
            )
        );
    }
    
    /**
     * Get conversation statistics
     */
    public function get_conversation_stats() {
        global $wpdb;
        
        // Create table name with prefix
        $table_name = $wpdb->prefix . 'luxe_chatbot_conversations';
        
        // Check if table exists, if not create it
        $this->maybe_create_tables();
        
        // Get total conversation count
        $total_count = $wpdb->get_var("SELECT COUNT(DISTINCT conversation_id) FROM $table_name");
        
        // Get conversations per day for the last 30 days
        $daily_stats = $wpdb->get_results("
            SELECT 
                DATE(created_at) as date,
                COUNT(DISTINCT conversation_id) as count
            FROM 
                $table_name
            WHERE 
                created_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)
            GROUP BY 
                DATE(created_at)
            ORDER BY 
                date ASC
        ");
        
        // Get average messages per conversation
        $avg_messages = $wpdb->get_var("
            SELECT 
                AVG(message_count) 
            FROM (
                SELECT 
                    conversation_id, 
                    COUNT(*) as message_count
                FROM 
                    $table_name
                GROUP BY 
                    conversation_id
            ) as t
        ");
        
        // Create stats array
        $stats = array(
            'total_conversations' => intval($total_count),
            'avg_messages_per_conversation' => round(floatval($avg_messages), 1),
            'daily_stats' => $daily_stats,
            'last_updated' => current_time('mysql')
        );
        
        return rest_ensure_response($stats);
    }
    
    /**
     * Get recent conversations
     */
    public function get_recent_conversations() {
        global $wpdb;
        
        // Create table name with prefix
        $table_name = $wpdb->prefix . 'luxe_chatbot_conversations';
        
        // Check if table exists
        $this->maybe_create_tables();
        
        // Get conversations grouped by conversation_id, limited to 50 most recent
        $conversations = $wpdb->get_results("
            SELECT 
                c1.conversation_id,
                MAX(c1.created_at) as last_message_time,
                COUNT(c1.id) as message_count
            FROM 
                $table_name c1
            GROUP BY 
                c1.conversation_id
            ORDER BY 
                last_message_time DESC
            LIMIT 50
        ");
        
        // For each conversation, get the first message (usually the user query)
        foreach ($conversations as &$conversation) {
            $first_message = $wpdb->get_row($wpdb->prepare("
                SELECT 
                    message_content,
                    message_type,
                    created_at
                FROM 
                    $table_name
                WHERE 
                    conversation_id = %s
                ORDER BY 
                    created_at ASC
                LIMIT 1
            ", $conversation->conversation_id));
            
            $conversation->first_message = $first_message ? $first_message->message_content : '';
            $conversation->created_at = $first_message ? $first_message->created_at : '';
        }
        
        return rest_ensure_response($conversations);
    }
    
    /**
     * Get common queries
     */
    public function get_common_queries() {
        global $wpdb;
        
        // Create table name with prefix
        $table_name = $wpdb->prefix . 'luxe_chatbot_conversations';
        
        // Check if table exists
        $this->maybe_create_tables();
        
        // Get common user queries (only messages from user)
        $common_queries = $wpdb->get_results("
            SELECT 
                message_content,
                COUNT(*) as frequency
            FROM 
                $table_name
            WHERE 
                message_type = 'user'
            GROUP BY 
                message_content
            HAVING 
                COUNT(*) > 1
            ORDER BY 
                frequency DESC
            LIMIT 20
        ");
        
        return rest_ensure_response($common_queries);
    }
    
    /**
     * Create database tables if they don't exist
     */
    private function maybe_create_tables() {
        global $wpdb;
        
        $table_name = $wpdb->prefix . 'luxe_chatbot_conversations';
        
        // Check if table exists
        if ($wpdb->get_var("SHOW TABLES LIKE '$table_name'") != $table_name) {
            // Table doesn't exist, create it
            $charset_collate = $wpdb->get_charset_collate();
            
            $sql = "CREATE TABLE $table_name (
                id bigint(20) NOT NULL AUTO_INCREMENT,
                conversation_id varchar(50) NOT NULL,
                message_content text NOT NULL,
                message_type varchar(10) NOT NULL,
                user_ip varchar(100),
                user_agent text,
                page_url varchar(255),
                created_at datetime DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY  (id),
                KEY conversation_id (conversation_id),
                KEY message_type (message_type),
                KEY created_at (created_at)
            ) $charset_collate;";
            
            require_once(ABSPATH . 'wp-admin/includes/upgrade.php');
            dbDelta($sql);
            
            // Create an access key for the public dashboard
            if (!get_option('luxe_chatbot_dashboard_key')) {
                $access_key = wp_generate_password(12, false);
                update_option('luxe_chatbot_dashboard_key', $access_key);
            }
        }
    }
    
    /**
     * Render admin dashboard page
     */
    public function render_dashboard_page() {
        // Check user capabilities
        if (!current_user_can('manage_options')) {
            return;
        }
        
        // Generate access key if it doesn't exist
        $access_key = get_option('luxe_chatbot_dashboard_key', '');
        if (empty($access_key)) {
            $access_key = wp_generate_password(12, false);
            update_option('luxe_chatbot_dashboard_key', $access_key);
        }
        
        $public_url = home_url('chatbot-dashboard/' . $access_key);
        
        ?>
        <div class="wrap luxe-chatbot-dashboard">
            <h1><?php echo esc_html(get_admin_page_title()); ?></h1>
            
            <div class="dashboard-header">
                <div class="stats-summary">
                    <div class="stat-card" id="total-conversations">
                        <h3>Total Conversations</h3>
                        <div class="stat-value">-</div>
                    </div>
                    <div class="stat-card" id="avg-messages">
                        <h3>Avg. Messages Per Conversation</h3>
                        <div class="stat-value">-</div>
                    </div>
                    <div class="stat-card" id="today-conversations">
                        <h3>Today's Conversations</h3>
                        <div class="stat-value">-</div>
                    </div>
                </div>
                
                <div class="actions">
                    <button type="button" class="button button-primary" id="refresh-stats">Refresh Data</button>
                    <div class="share-dashboard">
                        <p>Share this dashboard:</p>
                        <input type="text" readonly value="<?php echo esc_url($public_url); ?>" class="share-url" />
                        <button type="button" class="button copy-url">Copy</button>
                    </div>
                </div>
            </div>
            
            <div class="dashboard-main">
                <div class="dashboard-section">
                    <h2>Conversations Over Time</h2>
                    <div class="chart-container">
                        <canvas id="conversations-chart"></canvas>
                    </div>
                </div>
                
                <div class="dashboard-section">
                    <h2>Common User Queries</h2>
                    <div class="queries-container" id="common-queries">
                        <div class="loading">Loading data...</div>
                    </div>
                </div>
                
                <div class="dashboard-section">
                    <h2>Recent Conversations</h2>
                    <div class="conversations-container" id="recent-conversations">
                        <div class="loading">Loading data...</div>
                    </div>
                </div>
            </div>
            
            <div class="dashboard-footer">
                <p>Last updated: <span id="last-updated">-</span></p>
                <p>Note: This dashboard shows data from conversations stored in the database. Historical data may be limited if you've just installed this feature.</p>
            </div>
        </div>
        <?php
    }
    
    /**
     * Render public dashboard
     */
    public function render_public_dashboard() {
        // Include header
        ?>
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Luxe Mattresses Chatbot Dashboard</title>
            <link rel="stylesheet" href="<?php echo LUXE_CHATBOT_PLUGIN_URL . 'dashboard.css'; ?>">
            <style>
                body {
                    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Oxygen-Sans, Ubuntu, Cantarell, "Helvetica Neue", sans-serif;
                    background-color: #f1f1f1;
                    color: #333;
                    margin: 0;
                    padding: 20px;
                }
                
                .public-dashboard {
                    max-width: 1200px;
                    margin: 0 auto;
                    background: white;
                    border-radius: 5px;
                    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
                    padding: 20px;
                }
                
                .dashboard-header {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    margin-bottom: 20px;
                    flex-wrap: wrap;
                }
                
                @media (max-width: 768px) {
                    .dashboard-header {
                        flex-direction: column;
                        align-items: flex-start;
                    }
                    
                    .dashboard-header .logo {
                        margin-bottom: 15px;
                    }
                }
            </style>
        </head>
        <body>
            <div class="public-dashboard">
                <div class="dashboard-header">
                    <div class="logo">
                        <h1>Luxe Mattresses Chatbot Dashboard</h1>
                    </div>
                    <div class="refresh">
                        <button type="button" class="button button-primary" id="refresh-stats">Refresh Data</button>
                    </div>
                </div>
                
                <div class="dashboard-main">
                    <div class="stats-summary">
                        <div class="stat-card" id="total-conversations">
                            <h3>Total Conversations</h3>
                            <div class="stat-value">-</div>
                        </div>
                        <div class="stat-card" id="avg-messages">
                            <h3>Avg. Messages Per Conversation</h3>
                            <div class="stat-value">-</div>
                        </div>
                        <div class="stat-card" id="today-conversations">
                            <h3>Today's Conversations</h3>
                            <div class="stat-value">-</div>
                        </div>
                    </div>
                    
                    <div class="dashboard-section">
                        <h2>Conversations Over Time</h2>
                        <div class="chart-container">
                            <canvas id="conversations-chart"></canvas>
                        </div>
                    </div>
                    
                    <div class="dashboard-section">
                        <h2>Common User Queries</h2>
                        <div class="queries-container" id="common-queries">
                            <div class="loading">Loading data...</div>
                        </div>
                    </div>
                </div>
                
                <div class="dashboard-footer">
                    <p>Last updated: <span id="last-updated">-</span></p>
                    <p>Powered by Luxe Mattresses Chatbot</p>
                </div>
            </div>
            
            <script src="https://cdn.jsdelivr.net/npm/chart.js@3.7.1/dist/chart.min.js"></script>
            <script src="<?php echo includes_url('js/jquery/jquery.js'); ?>"></script>
            <script src="<?php echo LUXE_CHATBOT_PLUGIN_URL . 'dashboard.js'; ?>"></script>
            <script>
                // Initialize dashboard with public data
                jQuery(document).ready(function($) {
                    var dashboard = {
                        api_url: '<?php echo rest_url('luxe-chatbot/v1/'); ?>',
                        nonce: '<?php echo wp_create_nonce('wp_rest'); ?>',
                        is_public: true
                    };
                    
                    initDashboard(dashboard);
                });
            </script>
        </body>
        </html>
        <?php
        exit;
    }
}

/**
 * Log conversation to database
 * 
 * @param string $conversation_id Unique ID for this conversation
 * @param string $message_content The message content
 * @param string $message_type Type of message (user/bot)
 */
function luxe_chatbot_log_conversation($conversation_id, $message_content, $message_type) {
    global $wpdb;
    
    $table_name = $wpdb->prefix . 'luxe_chatbot_conversations';
    
    // Insert conversation
    $wpdb->insert(
        $table_name,
        array(
            'conversation_id' => $conversation_id,
            'message_content' => $message_content,
            'message_type' => $message_type,
            'user_ip' => $_SERVER['REMOTE_ADDR'],
            'user_agent' => $_SERVER['HTTP_USER_AGENT'],
            'page_url' => isset($_SERVER['HTTP_REFERER']) ? $_SERVER['HTTP_REFERER'] : '',
            'created_at' => current_time('mysql')
        )
    );
}