import { useEffect, useState, useCallback } from 'react';

export interface NotificationTask {
  id: number;
  title: string;
  due_date?: string;
  quadrant?: string;
}

export interface Notification {
  type: 'overdue' | 'deadline' | 'reminder';
  count: number;
  tasks: NotificationTask[];
  timestamp: string;
}

export interface UseNotificationsReturn {
  notifications: Notification[];
  clearNotification: (index: number) => void;
  clearAll: () => void;
  isConnected: boolean;
}

/**
 * Hook for receiving real-time notifications via Server-Sent Events (SSE).
 *
 * Connects to the backend notification stream and listens for:
 * - overdue: Tasks past their due date
 * - deadline: Tasks approaching their deadline
 * - reminder: Custom reminders set by the user
 *
 * @param userId - User ID to fetch notifications for
 * @param enabled - Whether to enable the notification stream (default: true)
 * @returns Notification state and management functions
 */
export function useNotifications(
  userId: number | null,
  enabled: boolean = true
): UseNotificationsReturn {
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [isConnected, setIsConnected] = useState(false);

  const clearNotification = useCallback((index: number) => {
    setNotifications(prev => prev.filter((_, i) => i !== index));
  }, []);

  const clearAll = useCallback(() => {
    setNotifications([]);
  }, []);

  useEffect(() => {
    if (!userId || !enabled) {
      setIsConnected(false);
      return;
    }

    // Get API URL from environment
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    const eventSource = new EventSource(
      `${apiUrl}/api/notifications/stream?user_id=${userId}`
    );

    eventSource.onopen = () => {
      console.log('[useNotifications] SSE connection opened');
      setIsConnected(true);
    };

    eventSource.onerror = (error) => {
      console.error('[useNotifications] SSE error:', error);
      setIsConnected(false);
    };

    // Listen for overdue task notifications
    eventSource.addEventListener('overdue', (event) => {
      try {
        const data = JSON.parse(event.data);
        const notification: Notification = {
          type: 'overdue',
          count: data.count || data.tasks?.length || 0,
          tasks: data.tasks || [],
          timestamp: new Date().toISOString(),
        };
        setNotifications(prev => [...prev, notification]);
      } catch (error) {
        console.error('[useNotifications] Failed to parse overdue event:', error);
      }
    });

    // Listen for approaching deadline notifications
    eventSource.addEventListener('deadline', (event) => {
      try {
        const data = JSON.parse(event.data);
        const notification: Notification = {
          type: 'deadline',
          count: data.count || data.tasks?.length || 0,
          tasks: data.tasks || [],
          timestamp: new Date().toISOString(),
        };
        setNotifications(prev => [...prev, notification]);
      } catch (error) {
        console.error('[useNotifications] Failed to parse deadline event:', error);
      }
    });

    // Listen for custom reminders
    eventSource.addEventListener('reminder', (event) => {
      try {
        const data = JSON.parse(event.data);
        const notification: Notification = {
          type: 'reminder',
          count: data.count || data.tasks?.length || 0,
          tasks: data.tasks || [],
          timestamp: new Date().toISOString(),
        };
        setNotifications(prev => [...prev, notification]);
      } catch (error) {
        console.error('[useNotifications] Failed to parse reminder event:', error);
      }
    });

    // Cleanup on unmount
    return () => {
      console.log('[useNotifications] Closing SSE connection');
      eventSource.close();
      setIsConnected(false);
    };
  }, [userId, enabled]);

  return {
    notifications,
    clearNotification,
    clearAll,
    isConnected,
  };
}
