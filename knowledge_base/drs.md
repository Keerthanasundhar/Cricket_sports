# Decision Review System (DRS)
_Starter summary written for this project. Replace/augment with the official ICC Playing Conditions._

## Purpose
DRS lets a team challenge an on-field umpire decision. The third umpire uses replays, edge detection
and ball-tracking to check it. Each team gets a limited number of unsuccessful reviews per innings
(the number depends on the format and competition).

## Umpire's call on LBW
Ball-tracking checks three things: where the ball pitched, where it hit the batter (impact), and
whether it would have gone on to hit the stumps. If the ball pitched outside leg stump the batter is
not out. If the tracked path shows the ball only marginally hitting the stumps (less than half the ball
inside the stump zone), or the impact is only marginally in line, the result is "umpire's call": the
original on-field decision stands. The wicket zone extends up to the top of the bails.

## What umpire's call means for the review
When a review returns umpire's call, the on-field decision is unchanged, and the reviewing team does
not lose its review. So a batter given out who reviews and gets "umpire's call" is still out but the
team keeps the review; a batter given not out stays not out, and the fielding team also keeps its review.

## Caveat
Details (review counts, extra uses such as wides and no-balls) differ by competition and season.
