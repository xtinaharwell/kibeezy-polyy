# Support System Implementation Guide

## Overview

A complete support ticketing system has been implemented with proper staff roles, ticket tracking, and a dedicated dashboard for support staff.

---

## System Components

### 1. **Database Models**

#### **SupportTicket**
- **ticket_id**: Auto-generated unique identifier (TK-00001, TK-00002, etc.)
- **user**: FK to CustomUser - the person who created the ticket
- **subject**: Ticket subject/title
- **status**: OPEN, IN_PROGRESS, RESOLVED, CLOSED
- **assigned_to**: FK to support staff member (optional)
- **created_at**: Ticket creation timestamp
- **updated_at**: Last update timestamp
- **resolved_at**: When the ticket was marked as resolved

#### **SupportMessage**
- **ticket**: FK to SupportTicket - links message to ticket
- **sender**: FK to CustomUser - who sent the message
- **message**: Message text content
- **is_from_user**: Boolean - True if from user, False if from support staff
- **created_at**: Message timestamp

#### **CustomUser (Extended)**
- **is_support_staff**: Boolean field to mark users as support staff

---

## How It Works

### **User Flow**
1. User clicks "Help" icon in navbar
2. Opens `SupportModal` component
3. Creates a new support ticket with subject and initial message
4. Receives ticket ID (e.g., "TK-00001")
5. Can view all their tickets at `/my-tickets/` endpoint
6. Can add replies to existing tickets
7. Support staff can view and update ticket status

### **Support Staff Flow**
1. Admin marks user as support staff: Go to Django admin → Users → Edit user → Check "is_support_staff"
2. Support staff logs in and navigates to `/dashboard/support`
3. Views dashboard with:
   - Filtered ticket list (by status & assignment)
   - Detailed view of selected ticket
   - Full message conversation history
   - Quick assignment to other staff members
4. Can update ticket status (OPEN → IN_PROGRESS → RESOLVED → CLOSED)
5. Can assign tickets to themselves or other staff
6. Can reply directly in the dashboard
7. Auto-saves messages as staff responses

---

## API Endpoints

### **User Endpoints**

**Get all user's tickets**
```
GET /api/support/my-tickets/
Response: List of SupportTicket objects
```

**Get specific ticket details**
```
GET /api/support/tickets/<ticket_id>/
Response: SupportTicket with messages array
```

**Create new support ticket**
```
POST /api/support/create/
Body: {
  "subject": "I can't withdraw my balance",
  "message": "When I try to withdraw, I get an error"
}
Response: New SupportTicket object
```

**Add reply to existing ticket**
```
POST /api/support/tickets/<ticket_id>/reply/
Body: {
  "message": "Thank you for the update"
}
Response: New SupportMessage object
```

### **Support Staff Endpoints**

**Get all tickets (with filters)**
```
GET /api/support/dashboard/tickets/
Query params:
  - status: OPEN, IN_PROGRESS, RESOLVED, CLOSED
  - assigned: all, me, unassigned

Response: List of SupportTicket objects
```

**Get ticket details (staff view)**
```
GET /api/support/dashboard/tickets/<ticket_id>/
Response: Full SupportTicket with messages
```

**Update ticket status or assignment**
```
PATCH /api/support/dashboard/tickets/<ticket_id>/update/
Body: {
  "status": "IN_PROGRESS",
  "assigned_to": 5  // User ID or null
}
Response: Updated SupportTicket
```

**Reply to ticket (staff)**
```
POST /api/support/dashboard/tickets/<ticket_id>/support-reply/
Body: {
  "message": "We're looking into this. Please wait 24 hours."
}
Response: New SupportMessage (is_from_user=False)
```

**Get all support staff members**
```
GET /api/support/dashboard/support-staff/
Response: List of support staff users
```

---

## Setup Instructions

### **Step 1: Make a User Support Staff**

Option A: Django Admin
```
1. Go to /admin/
2. Click "Users"
3. Select the user
4. Check "is_support_staff" checkbox
5. Save
```

Option B: Command Line
```python
from users.models import CustomUser
user = CustomUser.objects.get(phone_number="0718693484")
user.is_support_staff = True
user.save()
```

### **Step 2: Access Support Dashboard**

1. Log in as support staff user
2. Navigate to `/dashboard/support`
3. Dashboard loads with all tickets

### **Step 3: Manage Tickets**

- **Filter by Status**: Use dropdown to show OPEN, IN_PROGRESS, RESOLVED, CLOSED
- **Filter by Assignment**: View "All Tickets", "Assigned to Me", or "Unassigned"
- **Click Ticket**: Select from left sidebar to view details
- **Update Status**: Change status dropdown and it auto-saves
- **Assign Ticket**: Select staff member from assignment dropdown
- **Reply**: Type message and click Send - appears as support staff response

---

## Frontend Components

### **SupportModal** (User)
Location: `components/SupportModal.tsx`
- Allows users to create tickets
- View ticket history
- Add replies to tickets

### **Support Dashboard** (Staff)
Location: `app/dashboard/support/page.tsx`
- Ticket list with filtering
- Detailed ticket view
- Message conversation thread
- Status & assignment controls
- Reply composer

---

## Key Features

✅ **Ticket Tracking**: Auto-generated ticket IDs (TK-XXXXX)
✅ **Status Management**: OPEN → IN_PROGRESS → RESOLVED → CLOSED  
✅ **Staff Assignment**: Assign tickets to specific support staff
✅ **Message History**: Full conversation thread for each ticket
✅ **Real-time Updates**: Messages appear immediately after sending
✅ **Filtering & Search**: Filter by status and assignment
✅ **Role-based Access**: Only support staff can access dashboard
✅ **User Identification**: See which user created the ticket
✅ **Timestamps**: All messages & updates timestamped

---

## Example Workflows

### **User Creates Support Ticket**
```
1. User sees error on withdraw page
2. Clicks Help icon → SupportModal opens
3. Enters subject: "Withdraw error on Android"
4. Types message: "Getting 'invalid_amount' error"
5. Clicks "Create Ticket"
6. Gets ticket ID: "TK-00042"
7. Can view all their tickets anytime
```

### **Support Staff Responds**
```
1. Support staff logs in
2. Goes to /dashboard/support
3. Sees "TK-00042" in OPEN list
4. Clicks ticket to view details
5. Sees user's message and device info
6. Changes status to "IN_PROGRESS"
7. Types reply: "We'll check your account. Usually resolves in 2-4 hours"
8. Clicks Send
9. User sees response in their ticket conversation
10. When fixed, support staff changes status to "RESOLVED"
```

---

## Permissions & Security

- **Users**: Can only view/edit their own tickets
- **Support Staff** (is_support_staff=True): Can view all tickets
- **Admins** (is_superuser=True): Full system access

---

## Database Schema

```sql
-- Support Tickets
support_supportticket (
  id, ticket_id (unique), user_id, assigned_to_id, 
  subject, status, created_at, updated_at, resolved_at
)

-- Support Messages
support_supportmessage (
  id, ticket_id, sender_id, message, 
  is_from_user, created_at, updated_at
)

-- Custom User (Extended)
users_customuser (
  ...existing fields...,
  is_support_staff (Boolean, default False)
)
```

---

## Future Enhancements

- Email notifications on ticket updates
- Canned responses / templates
- Ticket priorities (Low, Medium, High, Critical)
- SLA tracking (response time, resolution time)
- Ticket categories/tags
- Escalation workflows
- Knowledge base integration
- Chatbot for FAQs
- Mobile app support
- Analytics dashboard (avg resolution time, etc.)

---

## Troubleshooting

**Support staff can't see dashboard**
- Verify `is_support_staff=True` in Django admin
- Clear browser cache and re-login
- Check browser console for API errors

**Tickets not loading**
- Verify API base URL in `.env.local`
- Check Django backend is running
- Verify staff user is authenticated

**Can't reply to ticket**
- Ensure ticket status isn't CLOSED
- Check message isn't empty
- Verify support staff role is assigned
