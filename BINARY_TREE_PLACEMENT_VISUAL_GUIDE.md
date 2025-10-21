# Binary Tree Placement - Visual Guide (বাংলা + English)

## 🌳 বাইনারি ট্রি কিভাবে কাজ করে? (How Binary Tree Works?)

### নিয়ম (Rules)
- প্রতিটি ইউজার সর্বোচ্চ **2 জন** কে সরাসরি তার নিচে রাখতে পারবে (left এবং right position)
- যদি কেউ **2 জনের বেশি** রেফার করে, তাহলে **spillover** হবে
- **Spillover** মানে অতিরিক্ত রেফারগুলো তার downline এর নিচে বসবে (BFS algorithm ব্যবহার করে)

---

## 📊 উদাহরণ ১: প্রথম 2 জন রেফার (First 2 Referrals)

### User A প্রথম 2 জনকে রেফার করলো: B এবং C

```
BEFORE (শুরুতে):
    A
   / \
  ?   ?

AFTER (2 জন রেফারের পর):
    A
   / \
  B   C
```

### ডাটাবেস রেকর্ড (Database Records):
```
User B:
  parent_id  = A  (direct referrer)
  upline_id  = A  (tree parent - same)
  position   = left
  level      = 1
  is_spillover = false

User C:
  parent_id  = A  (direct referrer)
  upline_id  = A  (tree parent - same)
  position   = right
  level      = 1
  is_spillover = false
```

✅ **এখানে `parent_id` এবং `upline_id` একই কারণ direct placement**

---

## 📊 উদাহরণ ২: 3য় এবং 4র্থ রেফার (3rd & 4th Referral - Spillover)

### User A আরও 2 জনকে রেফার করলো: D এবং E

```
STEP 1: Check A's direct positions
    A
   / \
  B   C  ← Both positions FILLED!
  
STEP 2: Use BFS - Check B's positions
    A
   / \
  B   C
 / \
?  ?  ← B has space! Place here

STEP 3: Place D and E under B
    A
   / \
  B   C
 / \
D   E
```

### ডাটাবেস রেকর্ড (Database Records):
```
User D:
  parent_id  = A  (direct referrer - SAME)
  upline_id  = B  (tree parent - DIFFERENT!)
  position   = left
  level      = 2
  is_spillover = TRUE  ← এটা spillover placement

User E:
  parent_id  = A  (direct referrer - SAME)
  upline_id  = B  (tree parent - DIFFERENT!)
  position   = right
  level      = 2
  is_spillover = TRUE  ← এটা spillover placement
```

✅ **এখানে `parent_id` ≠ `upline_id` কারণ spillover placement**

---

## 📊 উদাহরণ ৩: 5ম এবং 6ষ্ঠ রেফার (5th & 6th Referral - More Spillover)

### User A আরও 2 জনকে রেফার করলো: F এবং G

```
CURRENT TREE:
    A
   / \
  B   C
 / \
D   E

STEP 1: Check A's positions → Filled (B, C)
STEP 2: Check B's positions → Filled (D, E)
STEP 3: Check C's positions → Available!

AFTER placing F and G:
    A
   / \
  B   C
 / \ / \
D  E F  G
```

### ডাটাবেস রেকর্ড (Database Records):
```
User F:
  parent_id  = A  (direct referrer)
  upline_id  = C  (tree parent - spillover)
  position   = left
  level      = 2
  is_spillover = TRUE

User G:
  parent_id  = A  (direct referrer)
  upline_id  = C  (tree parent - spillover)
  position   = right
  level      = 2
  is_spillover = TRUE
```

---

## 📊 উদাহরণ ৪: 7ম রেফার (7th Referral - Level 3)

### User A আরও 1 জনকে রেফার করলো: H

```
CURRENT TREE:
      A
     / \
    B   C
   / \ / \
  D  E F  G  ← All Level 2 positions filled!

STEP 1: Check A → Filled
STEP 2: Check B → Filled (D, E)
STEP 3: Check C → Filled (F, G)
STEP 4: Check D → Available! (Level 3)

AFTER placing H:
      A
     / \
    B   C
   / \ / \
  D  E F  G
 /
H
```

### ডাটাবেস রেকর্ড (Database Record):
```
User H:
  parent_id  = A  (direct referrer - still A!)
  upline_id  = D  (tree parent - Level 3 spillover)
  position   = left
  level      = 3
  is_spillover = TRUE
```

---

## 🎯 BFS Algorithm Step by Step

### যখন User A কাউকে refer করে, এই steps follow হয়:

```
QUEUE = [A]  ← Start with referrer
VISITED = {}

WHILE QUEUE is not empty:
  current_user = QUEUE.pop(0)
  
  IF current_user.left is EMPTY:
    ✅ PLACE HERE (left position)
    RETURN
  
  IF current_user.right is EMPTY:
    ✅ PLACE HERE (right position)
    RETURN
  
  ELSE:
    QUEUE.add(current_user.left_child)
    QUEUE.add(current_user.right_child)
    CONTINUE to next iteration
```

### উদাহরণ - 5ম User F কোথায় বসবে?

```
Iteration 1:
  Check A → left=B (filled), right=C (filled)
  Add B and C to queue
  Queue: [B, C]

Iteration 2:
  Check B → left=D (filled), right=E (filled)
  Add D and E to queue
  Queue: [C, D, E]

Iteration 3:
  Check C → left=? (EMPTY!)
  ✅ Place F here!
  
Result:
  F's upline_id = C
  F's position = left
  F's level = 2
```

---

## 💰 Commission Distribution (কমিশন বন্টন)

### Scenario: User A রেফার করেছে B, C, D, E, F, G (6 জন)

```
Tree Structure:
      A
     / \
    B   C
   / \ / \
  D  E F  G
```

### 1️⃣ Partner Incentive (Direct Referral Commission)
```
A gets commission from: B, C, D, E, F, G (all 6)
Why? → parent_id = A for all
```

### 2️⃣ Level Income (Tree Structure Commission)
```
Level 1 from A's perspective:
  A → B, C (2 users)
  
Level 2 from A's perspective:
  A → D, E, F, G (4 users, but through B and C)

B gets level income from: D, E (his tree children)
C gets level income from: F, G (his tree children)

Why? → Uses upline_id for tree structure
```

### 3️⃣ Binary Auto-Upgrade
```
A's partner count = 6 (all direct referrals)
Why? → Counts parent_id relationships

If auto-upgrade requires 2 partners → A qualifies ✅
```

---

## 📋 Summary Table (সারাংশ টেবিল)

| User | Direct Referrer | Tree Parent | Position | Level | Spillover? |
|------|----------------|-------------|----------|-------|------------|
| B    | A              | A           | left     | 1     | ❌         |
| C    | A              | A           | right    | 1     | ❌         |
| D    | A              | B           | left     | 2     | ✅         |
| E    | A              | B           | right    | 2     | ✅         |
| F    | A              | C           | left     | 2     | ✅         |
| G    | A              | C           | right    | 2     | ✅         |

---

## 🔍 API Response Example

### GET `/binary/duel-tree-earnings/user17608872172129581`

```json
{
  "tree": {
    "userId": "user17608872172129581",
    "totalMembers": 6,
    "levels": 2,
    "nodes": [
      {
        "id": 0,
        "type": "self",
        "userId": "user17608872172129581",
        "level": 0,
        "position": "root",
        "directDownline": [
          {
            "id": 1,
            "type": "downLine",
            "userId": "userB",
            "level": 1,
            "position": "left",
            "directDownline": [
              {"id": 2, "userId": "userD", "level": 2, "position": "left"},
              {"id": 3, "userId": "userE", "level": 2, "position": "right"}
            ]
          },
          {
            "id": 4,
            "type": "downLine",
            "userId": "userC",
            "level": 1,
            "position": "right",
            "directDownline": [
              {"id": 5, "userId": "userF", "level": 2, "position": "left"},
              {"id": 6, "userId": "userG", "level": 2, "position": "right"}
            ]
          }
        ]
      }
    ]
  }
}
```

### Tree Visualization from Response:
```
       user17608872172129581 (root)
              / \
         userB   userC (level 1)
         / \      / \
     userD userE userF userG (level 2)
```

---

## ✅ Key Takeaways (মূল কথা)

1. **2 জনের বেশি refer করলে spillover হবে** ✅
2. **parent_id = সরাসরি যে রেফার করেছে** (কমিশনের জন্য)
3. **upline_id = ট্রিতে যার নিচে বসেছে** (tree structure এর জন্য)
4. **BFS algorithm ব্যবহার করে সবচেয়ে কাছের খালি position খুঁজে নেয়** 🔍
5. **Level by level placement হয় (balanced tree)** ⚖️

---

## 🎊 এখন আপনি যত খুশি refer করতে পারবেন!

- 1st, 2nd → Direct placement (Level 1)
- 3rd, 4th → Spillover under 1st downline (Level 2)
- 5th, 6th → Spillover under 2nd downline (Level 2)
- 7th, 8th → Spillover under 3rd downline (Level 3)
- ... এভাবে চলতে থাকবে!

**সব ঠিকঠাক কাজ করবে! 🚀**

