---
tags : [maint-july26]
title : "Penalty Policy"
date : 2026-08-12
---

I am grateful to you all for standing in to support me in this difficult feature implementation for the penalties. Especially I would like to call out @Digvijay Verma G1 and @Prashant Sikdar Sikdar T1 Mana for spending almost 2 hours late night call to straighten out few lose ends of the penalty policy. We finished out discussion only nearing midnight. Here is the udpate - 
We are continuing with the logic of levying penalty based on the earlier communication as follows - 

```python
if (a flat is in negative balance)
    and no payment was done in the last two months, 
        apply a penalty for 1K for the current month.
```

we were discussing of improving the policy to be like below, so that we can penalize the defaulters who are not paying their full dues.

```python
if (a flat is in negative balance)
    if (no payment was done in the last two months) or (total outstanding in the current FY >= x%)
        apply a penalty for 1K for the current month.
```
But then point was what is the right x%? Should it be tight like 80-90% or median like 50%? There were different thoughts on this. 
Then, we agreed upon the point is that our intension is not to penalize anyone. But to remind people who just forget paying as our first step. A fine of 1K when it comes to everyone's notice, they might be more attentive towards prioritizing the payment of dues. 

And people who are intentionally not paying, we can always wait and watch, and again start a new thread of discussion to take this penality policy to version 2, where we incorporate additional nuances. 

So, we are going ahead with the 1st policy only. The portal is already live with this policy. 

And thank you @Shyam Nair for your note at the main group. That gave lots of strength and support to all of us. Feels good to be part of this team! We are building something beautiful - one small step at a time!