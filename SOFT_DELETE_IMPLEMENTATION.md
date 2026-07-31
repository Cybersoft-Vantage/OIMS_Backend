# Soft Delete Implementation with Dependency Checking

## Overview
This document explains the soft delete implementation for Categories, SubCategories, and AssetStatus in the OIMS system.

## Features

### 1. **Soft Delete (Not Hard Delete)**
- When you delete a category, subcategory, or status, it's not permanently removed from the database
- Records are marked with `IsDeleted = 1` and `DeletedAt` timestamp
- This preserves all asset history and audit trails

### 2. **Dependency Checking**
Before deletion, the system checks if the item is in use:

#### Category
- Checks if any assets are assigned to this category
- If found, deletion is blocked with message: "Cannot delete category. It is assigned to X asset(s)."

#### SubCategory
- Checks if any assets or components are assigned to this subcategory
- If found, deletion is blocked with message: "Cannot delete subcategory. It is assigned to X asset(s) and Y component(s)."

#### AssetStatus
- Checks if any assets have this status assigned
- If found, deletion is blocked with message: "Cannot delete status. It is assigned to X asset(s)."

### 3. **Query Filtering**
Normal queries automatically exclude soft-deleted items:
- `GET /assets/categories` - Shows only active categories
- `GET /assets/subcategories` - Shows only active subcategories
- `GET /assets/statuses` - Shows only active statuses

### 4. **Admin Audit Endpoints**
New endpoints to view deleted items for administrative purposes:
- `GET /assets/categories/deleted` - View all deleted categories
- `GET /assets/subcategories/deleted` - View all deleted subcategories
- `GET /assets/statuses/deleted` - View all deleted statuses

## Database Changes

Three columns were added to the database tables:

```sql
-- Categories table
ALTER TABLE Categories ADD COLUMN IsDeleted INT DEFAULT 0;
ALTER TABLE Categories ADD COLUMN DeletedAt DATETIME NULL;

-- SubCategories table
ALTER TABLE SubCategories ADD COLUMN IsDeleted INT DEFAULT 0;
ALTER TABLE SubCategories ADD COLUMN DeletedAt DATETIME NULL;

-- AssetStatus table
ALTER TABLE AssetStatus ADD COLUMN IsDeleted INT DEFAULT 0;
ALTER TABLE AssetStatus ADD COLUMN DeletedAt DATETIME NULL;
```

### Run Migration Script
To add these columns to your database, run:

```bash
cd Backend/fastapi_backend
python add_soft_delete_columns.py
```

## API Responses

### Success Response (HTTP 200)
```json
{
  "CategoryId": 1,
  "CategoryName": "Computers",
  "Description": "Desktop and laptop computers",
  "IsActive": 1
}
```

### Conflict Response (HTTP 409) - Item in Use
```json
{
  "detail": "Cannot delete category. It is assigned to asset(s)."
}
```

### Not Found Response (HTTP 404)
```json
{
  "detail": "Category not found"
}
```

## Frontend Considerations

### Delete Button Behavior
When user clicks delete:
1. Frontend sends DELETE request
2. If HTTP 409 is returned: Show error message to user
   - "Cannot delete this item. It is currently assigned to X items."
   - Offer option to view dependent items
3. If HTTP 200 is returned: Item deleted successfully

### Example Error Handling (Angular)
```typescript
deleteCategory(categoryId: number): void {
  this.categoryService.delete(categoryId).subscribe(
    (response) => {
      this.toastr.success('Category deleted successfully');
      this.loadCategories();
    },
    (error) => {
      if (error.status === 409) {
        this.toastr.error(error.error.detail);
      } else {
        this.toastr.error('An error occurred while deleting the category');
      }
    }
  );
}
```

## Restoring Deleted Items

Currently, deleted items are soft-deleted but not restorable through the UI. To restore a deleted item, you can either:

1. **Via Admin Panel** (future feature):
   - Access the deleted items list
   - Click restore button

2. **Via Direct Database Update**:
```sql
UPDATE Categories SET IsDeleted = 0, DeletedAt = NULL WHERE CategoryId = 1;
```

To implement restore functionality, add this to crud.py:
```python
def restore_category(db: Session, category_id: int):
    category = db.query(models.Category).filter(
        models.Category.CategoryId == category_id,
        models.Category.IsDeleted == 1
    ).first()
    if not category:
        return None
    category.IsDeleted = 0
    category.DeletedAt = None
    db.commit()
    db.refresh(category)
    return category
```

## Asset History Integration

Asset History records automatically capture all activities:
- When an asset is assigned to a category/subcategory
- When an asset status changes
- Even after the category/subcategory/status is soft-deleted

This ensures complete audit trails are maintained.

## Testing

### Test Case 1: Delete Unused Category
```bash
# Should succeed
DELETE /assets/categories/1
# Response: HTTP 200
```

### Test Case 2: Delete Used Category
```bash
# Should fail
DELETE /assets/categories/1
# Response: HTTP 409 - "Cannot delete category. It is assigned to X asset(s)."
```

### Test Case 3: View Deleted Categories
```bash
GET /assets/categories/deleted
# Shows all soft-deleted categories
```

## Benefits

1. **Data Integrity**: No data loss, all references remain valid
2. **Audit Trail**: Complete history of all changes
3. **Compliance**: Meets data retention requirements
4. **User-Friendly**: Clear error messages when items can't be deleted
5. **Admin Control**: View and manage deleted items separately
