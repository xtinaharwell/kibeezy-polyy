# Quick Start: Support System

## What Was Built

✅ **Ticket System** - Users create support tickets with auto-generated IDs (TK-00001, etc.)
✅ **Role System** - Mark users as "Support Staff" to give them access to dashboard
✅ **Support Dashboard** - Full UI at `/dashboard/support` for support team
✅ **Ticket Management** - Change status, assign to staff, reply to users

---

## Quick Setup (5 minutes)

### 1️⃣ Make Someone a Support Staff Member

**Via Django Admin:**
```
1. Go to http://localhost:8000/admin/
2. Click "Users" → Select a user
3. Check the checkbox: "User can view and respond to support tickets"
4. Click Save
```

**Via Python Shell:**
```bash
python manage.py shell
>>> from users.models import CustomUser
>>> user = CustomUser.objects.get(phone_number="0718693484")
>>> user.is_support_staff = True
>>> user.save()
```

### 2️⃣ Users Create Support Tickets

In the app:
1. Click **Help** icon in navbar
2. Click **Create Ticket**
3. Enter **Subject** and **Message**
4. Get a ticket ID (e.g., "TK-00001")
5. System saves conversation

### 3️⃣ Support Staff Views Dashboard

Support staff logs in and goes to: **`/dashboard/support`**

Dashboard shows:
- 📋 List of all tickets (left sidebar)
- 🎯 Filter by Status (OPEN, IN_PROGRESS, RESOLVED, CLOSED)
- 🏷️ Filter by Assignment (All, Assigned to Me, Unassigned)
- 💬 Full conversation for selected ticket
- ⚙️ Buttons to change status & assign

---

## How to Use the Dashboard

### Viewing Tickets
```
Left sidebar → Click any ticket to see full details
```

### Changing Status
```
Select ticket → Status dropdown → Choose: OPEN → IN_PROGRESS → RESOLVED → CLOSED
```

### Assigning Tickets
```
Select ticket → Assign To dropdown → Select support staff member
(Only shows users marked as support staff)
```

### Replying to Users
```
Select ticket → Type in message box → Click "Send"
Appears as support staff reply in conversation
```

---

## API Endpoints (For Developers)

### Create Ticket
```
POST /api/support/create/
{
  "subject": "Can't withdraw balance",
  "message": "Getting error when I try to withdraw"
}
```

### Get All User's Tickets
```
GET /api/support/my-tickets/
```

### Dashboard Endpoints (Support Staff Only)
```
GET /api/support/dashboard/tickets/  (with filters)
PATCH /api/support/dashboard/tickets/<ticket_id>/update/  (change status)
POST /api/support/dashboard/tickets/<ticket_id>/support-reply/  (send reply)
```

---

## Database Changes Made

✅ Added `is_support_staff` field to CustomUser
✅ Created `SupportTicket` model (replaces old system)
✅ Updated `SupportMessage` to reference tickets
✅ Ran migrations: `python manage.py migrate`

---

## Testing the System

### Test as Regular User:
1. Log in as any user
2. Click Help icon
3. Create a ticketnpm
4. See ticket ID assigned
5. Can add replies

### Test as Support Staff:
1. Make user support staff in admin
2. Log out and log back in
3. Go to `/dashboard/support`
4. See all tickets
5. Click ticket → Update status → Reply to user

---

## Common Issues

| Issue | Solution |
|-------|----------|
| Dashboard returns 403 error | User isn't marked as support staff in admin |
| Can't see tickets in dashboard | Make sure you're logged in as support staff |
| Replies not appearing | Refresh page or check API errors in console |
| Ticket won't create | Check that subject and message aren't empty |

---

## Status Workflow

```
OPEN → IN_PROGRESS → RESOLVED → CLOSED

OPEN: New ticket
IN_PROGRESS: Someone is working on it
RESOLVED: Issue fixed, waiting for user confirmation  
CLOSED: Fully completed, no more updates
```

---

## User vs Support Staff Difference

| User | Support Staff |
|------|--------------|
| Can create tickets | Can view ALL tickets |
| Can see own tickets | Can assign tickets |
| Can add replies | Can change status |
| | Can reply from dashboard |
| | See ticket IDs (TK-00001) |

---

That's it! You now have a full support ticketing system. 🎉
