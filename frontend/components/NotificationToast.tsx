"use client";

import React from "react";
import { X, AlertCircle, Clock, Bell } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Notification } from "@/lib/useNotifications";
import { cn } from "@/lib/utils";

interface NotificationToastProps {
  notification: Notification;
  onDismiss: () => void;
  onView?: () => void;
}

/**
 * Toast notification component for displaying task reminders and alerts.
 *
 * Displays different styles based on notification type:
 * - overdue: Red border, alert icon
 * - deadline: Yellow border, clock icon
 * - reminder: Blue border, bell icon
 */
export function NotificationToast({
  notification,
  onDismiss,
  onView,
}: NotificationToastProps) {
  const { type, count, tasks } = notification;

  // Determine icon and styling based on notification type
  const getNotificationStyle = () => {
    switch (type) {
      case 'overdue':
        return {
          icon: AlertCircle,
          iconColor: 'text-red-600',
          borderColor: 'border-l-red-600',
          bgColor: 'bg-red-50 dark:bg-red-950/20',
          title: 'Overdue Tasks',
          description: `You have ${count} overdue task${count !== 1 ? 's' : ''}`,
        };
      case 'deadline':
        return {
          icon: Clock,
          iconColor: 'text-yellow-600',
          borderColor: 'border-l-yellow-600',
          bgColor: 'bg-yellow-50 dark:bg-yellow-950/20',
          title: 'Upcoming Deadlines',
          description: `${count} task${count !== 1 ? 's' : ''} approaching deadline`,
        };
      case 'reminder':
        return {
          icon: Bell,
          iconColor: 'text-blue-600',
          borderColor: 'border-l-blue-600',
          bgColor: 'bg-blue-50 dark:bg-blue-950/20',
          title: 'Reminder',
          description: `${count} reminder${count !== 1 ? 's' : ''}`,
        };
      default:
        return {
          icon: Bell,
          iconColor: 'text-gray-600',
          borderColor: 'border-l-gray-600',
          bgColor: 'bg-gray-50 dark:bg-gray-950/20',
          title: 'Notification',
          description: `${count} notification${count !== 1 ? 's' : ''}`,
        };
    }
  };

  const style = getNotificationStyle();
  const Icon = style.icon;

  return (
    <Card
      className={cn(
        'fixed bottom-4 right-4 w-96 border-l-4 shadow-lg',
        style.borderColor,
        style.bgColor,
        'animate-in slide-in-from-bottom-5 duration-300'
      )}
    >
      <div className="p-4">
        {/* Header */}
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-start gap-3 flex-1">
            <Icon className={cn('h-5 w-5 mt-0.5', style.iconColor)} />
            <div className="flex-1 min-w-0">
              <h3 className="font-semibold text-sm">{style.title}</h3>
              <p className="text-sm text-muted-foreground mt-1">
                {style.description}
              </p>

              {/* Task list */}
              {tasks.length > 0 && (
                <ul className="mt-2 space-y-1">
                  {tasks.slice(0, 3).map((task, index) => (
                    <li
                      key={task.id || index}
                      className="text-sm text-muted-foreground truncate"
                    >
                      • {task.title}
                    </li>
                  ))}
                  {tasks.length > 3 && (
                    <li className="text-sm text-muted-foreground italic">
                      ... and {tasks.length - 3} more
                    </li>
                  )}
                </ul>
              )}
            </div>
          </div>

          {/* Close button */}
          <Button
            variant="ghost"
            size="sm"
            className="h-6 w-6 p-0 hover:bg-transparent"
            onClick={onDismiss}
          >
            <X className="h-4 w-4" />
          </Button>
        </div>

        {/* Actions */}
        <div className="flex items-center gap-2 mt-4">
          {onView && (
            <Button
              variant="default"
              size="sm"
              onClick={() => {
                onView();
                onDismiss();
              }}
            >
              View Tasks
            </Button>
          )}
          <Button variant="ghost" size="sm" onClick={onDismiss}>
            Dismiss
          </Button>
        </div>
      </div>
    </Card>
  );
}
