# Nudge — Campaign Targeting Project Playbook

Oct 21, 2026 · @vipul

Nudge is a next-best-offer and budget engine: for each customer it decides whether to make contact, which offer to send (reminder, discount or credit), and how to split a fixed marketing budget for the most profit, with impact proven by randomized experiments. The core is an uplift model trained on 200,039 grocery customers and 45.8M purchases; two further public experiments add offer types and revenue. Early result: the message lifted buying by 3.3 points overall, and 4 to 5 times more among older customers than younger ones. The model is the asset; the datasets are training sources, so the same pipeline applies to any Indian company's customer table.

## 1. The problem

Companies pay for every coupon, SMS and push notification, but much of that spend goes to customers who would have bought anyway.

- Most campaign reports count everyone who bought after the message as a success, which overstates the return.
- Indian quick-commerce and D2C brands spend heavily on discounts and ads; quick-commerce advertising alone is projected at about Rs 6,000 crore in 2026.
- The question a marketing or growth head needs answered: **did the campaign cause extra purchases, for whom, and where should the next rupee go?**

### The business question Nudge answers

A growth or CRM head needs one decision per customer, inside a budget, with proof that it worked.

| # | Question | Plain meaning |
| --- | --- | --- |
| Q1 | Whether to contact? | Does contacting this customer cause extra buying? |
| Q2 | What to send? | Reminder, discount or credit: which works best for this customer? |
| Q3 | How to spend the budget? | With a fixed amount, who gets what for the most total profit? |
| Q4 | How to keep measuring? | How to run every future campaign so impact stays provable |

## Why this project: five fundamental questions

### 1. Why does this project exist, and who needs it?

**The problem in one line:** companies spend heavily on messages, discounts and cashback, but a large part of that money goes to customers who would have bought anyway, and some goes to customers it pushes away.

- **Waste:** a ₹50 discount sent to a regular shopper is mostly a gift; they were buying anyway (Step 8, B4: it would need a 30-point jump in buying to pay).
- **False success:** campaign reports count every purchase after a message as a win, so ROI looks great even when the campaign changed nothing (the Complete Journey contrast case: naive reports showed 3 to 5.6 times more spend; the fair effect was about −7% to +11%).
- **Limited budget:** WhatsApp messages, calls and offers cost real money, so every rupee should go where it changes behaviour.

**Who uses this:** CRM, growth and marketing teams in any business with repeat customers and paid nudges: quick commerce and food delivery (discount codes), payments and fintech apps (cashback), banks and NBFCs (cross-sell calls), home-loan lenders (lead follow-up calls), D2C brands, retail loyalty programmes, telecom (recharge offers).

**What Nudge gives them:** for every customer, one answer — contact or not, with what, through which channel — plus the rupee profit of the plan and a fair way to prove it worked.

### 2. If the goal is maximum profit, why not message and offer everyone?

Because every contact and every offer has a cost, and customers react differently. The four customer types:

| Customer type | Without message | With message | Pay to contact? |
| --- | --- | --- | --- |
| Persuadable | Doesn't buy | Buys | **Yes: the only real profit** |
| Sure thing | Buys | Buys | No: you pay for a sale you already had |
| Lost cause | Doesn't buy | Doesn't buy | No: wasted cost |
| Do-not-disturb | Buys | Doesn't buy | **Never: the message loses a sale** |

Four reasons not to contact everyone:

1. **Offers are paid to sure things too.** A discount is given to every buyer, including those who would buy anyway. That is why blanket discounts destroy margin.
2. **Some customers react badly.** In X5, the bottom 5% bought less when messaged.
3. **Budgets and channels are limited.** Calls, WhatsApp and offers cost money; a capped budget must go to the highest return first (Step 8: ₹2.44 lakh vs ₹3,300 for the same ₹20k).
4. **Hidden long-term costs.** Over-messaging causes unsubscribes, DND complaints and app uninstalls, and constant discounts teach customers to wait for the next one.

**Important:** Nudge is not against contacting people. It maximises profit. When the contact is cheap and harmless (SMS, no offer), its answer is "contact 95%". It only holds back where contacting loses money.

### 3. What did the model learn from, and how?

**The persona and buying-pattern intuition is right, with one crucial twist.**

- **What it looks at:** each customer's buying pattern before the campaign: 67 measures (Step 2) covering recency, frequency, money spent (RFM), purchase rhythm, trend (slowing down or speeding up), basket habits, loyalty points, promo-point use, store loyalty, time-of-day habits, card age, age and gender, plus our own overdue ratio (days away ÷ usual gap).
- **What it learns:** not "who buys", but "**who buys because of the nudge**". The company ran a fair test: half the customers were messaged and half were not, at random. For customers with a similar pattern, the model compares the buy rate of the messaged ones with the not-messaged ones. The difference is the **uplift**.
- **The twist:** a model that learns only from buying patterns picks likely buyers, who are mostly sure things. That approach made only ₹3,300 on a ₹20k budget. Learning the *response to the nudge* made ₹2.44 lakh.
- **Personas:** instead of hand-made persona groups, the model finds thousands of fine-grained patterns automatically, then we summarise them into personas a marketer can use (Step 5: the nudgeable 17%, lift 6.4 points; the average 74%, 2.9; the loyal regular 9%, 1.2).

| Approach | Learns | Picks | Result on a ₹20k budget |
| --- | --- | --- | --- |
| Likely-buyer (usual) | Who buys | Sure things | ₹3,300 |
| Random | Nothing | Anyone | ₹99,600 |
| **Uplift (Nudge)** | **Who buys because of the nudge** | **Persuadables** | **₹2.44 lakh** |

### 4. How do the offer choice and the rupee optimisation work?

1. **One uplift model per option** (reminder, discount, free item, …) predicts, for each customer, the extra buying that option causes (Step 7 engine).
2. **The money equation** turns it into rupees: extra buyers × margin − reward × everyone who uses it − contact cost. Each option has its own cost rule (a discount costs its face value; a free item costs only its cost of goods; cashback costs only what is redeemed).
3. **Pick the best option per customer**, or the best single option for all when personalising does not reliably pay.
4. **Rank customers by rupee gain** and fund them in order until the budget runs out.
5. **Check on locked test customers** with 95% ranges, and stress-test the assumptions.

This is not price-setting (changing the product price). It optimises **who gets what, and how much budget to spend**. Testing different offer amounts (₹30 vs ₹50) needs a pilot with those amounts; B4 says which amounts are worth testing.

### 5. Do we pick the best time to send?

**Partly, and honestly not yet fully.**

- **What we have:** the model uses timing-related patterns (days since last visit, overdue ratio, purchase rhythm, time-of-day habits), so "is this customer at a responsive moment now?" is already inside the score.
- **What the data shows:** in X5, the extra buying from the message is about the same whether a customer has just shopped or is overdue:

| Where the customer is in their cycle | Share | Lift from message |
| --- | --- | --- |
| Just bought (overdue ratio under 0.25) | 32% | 3.1 pts |
| 0.25 to 0.5 | 19% | 3.5 pts |
| Due soon (0.5 to 1) | 23% | 3.3 pts |
| Overdue (1 to 2) | 17% | 3.0 pts |
| Lapsing (over 2) | 8% | 3.9 pts |

The ranges overlap, so in this data **who** matters far more than **when** (persona lift ranges from 1.2 to 6.4 points).

- **What we cannot claim:** the best hour or day to send. X5 sent every message at one moment, so send time was never tested. Measuring it needs a pilot where send time is randomised (for example morning vs evening, or day 3 vs day 7 after the last purchase). The Step 9 measurement playbook includes this as a recommended test.

## 2. The solution flow

Raw data passes through six stages to become a ranked target list with a money view; each gate (K1 to K5) must pass before the next stage counts.

&#91;embedded content: solution flow · 6 stages from data to product\]

Stages 1 to 3 build trust in the data, stage 4 is the analytical core, and stages 5 and 6 turn the analysis into a business decision and a usable tool.

## 3. The data

The core dataset is X5 RetailHero: a grocery chain sent a message to a random half of its loyalty customers and recorded who bought afterwards. Its three files link on `client_id`.

| File | Rows | What one row is | Key columns |
| --- | --- | --- | --- |
| uplift\_train | 200,039 | A customer in the experiment | treatment\_flg (1 = got the message), target (1 = bought afterwards) |
| clients | 400,162 | A loyalty customer | age, gender, card issue date, first points-use date |
| purchases | about 45.8M | One item in one shopping trip, before the message | date, bill total, store, product, quantity, amount paid, points earned and spent |

- **clients** holds twice the experiment's customers; the other half was the hackathon's hidden test set, so only the matching 200,039 are used.
- **purchases** is rolled up from items to trips, then to one profile per customer, before any modelling.
- **Supporting dataset: Dunnhumby Complete Journey** (2,469 US households, one year, 27 company-chosen campaigns). Used only to show how misleading ROI becomes when targeting is not random.
- **Limits:** no message cost or profit margin (money results use stated assumptions, shown as ranges); not Indian data (the India angle comes from the memo).

### Context: company, campaign and timeline

X5 is Russia's largest grocery retailer; it sent one marketing communication to a random half of its loyalty customers and recorded who bought afterwards.

| Question | Answer | Confidence |
| --- | --- | --- |
| Who is the company? | X5 Retail Group: Pyaterochka neighbourhood stores, Perekrestok supermarkets, Karusel hypermarkets | Confirmed |
| What do they sell? | Everyday groceries and household goods | Confirmed |
| What is the loyalty card? | Likely Pyaterochka's points card: earn about 1 point per 10 to 20 roubles, 10 points = 1 rouble off; physical card, scanned at every checkout | Card type inferred; programme details confirmed |
| Why do purchases show points? | The card is scanned on every trip, so each trip records points earned and spent; express points are promotional bonus points | Confirmed |
| What is first\_redeem\_date? | The first day the customer ever paid with points, not a purchase date | Confirmed |
| What was the treatment? | One marketing communication, yes or no; write-ups describe it as an SMS; content (reminder or offer) not stated | Yes/no confirmed; SMS unverified |
| Whose history is in purchases? | All 400,162 card holders; we use the 200,039 in the experiment | Confirmed |
| What period? | A few months just before the communication, not all time; write-ups say about Nov 2018 to Mar 2019 | Before-campaign confirmed; dates checked in step 2 |

Timeline: **purchase history (before) → one communication to a random 50% → purchase window (after) = target.**

Confirmed in Step 1: purchase history runs **21 Nov 2018 to 18 Mar 2019**; the message and the target window come after 18 Mar 2019. Full detail in section 7, Step 1.

### Additional datasets: filling the offer-type gap

X5 has one communication of unknown content, so it answers Q1 only; two more public experiments cover offer types, revenue and costs.

| Dataset | What it holds | Real or simulated | Answers |
| --- | --- | --- | --- |
| X5 RetailHero (core) | 200,039 customers, one communication, random 50/50, 45.8M past purchases | Real, randomized | Q1, Q4 |
| Hillstrom email experiment | About 64,000 customers given a men's email, women's email or none at random; outcomes: visit, purchase, amount spent | Real, randomized | Q2, revenue lift |
| Starbucks rewards data | About 17,000 customers; 10 offers (discount, buy-one-get-one, information only) with reward value and spend threshold | Simulated by Starbucks for teaching | Q2, Q3 (offer types and costs) |

- Hillstrom and Starbucks details are from memory; verified when downloaded.
- Starbucks is used only to demonstrate the offer-choice and budget engine, and is labelled simulated wherever it appears.
- The model, not the dataset, is the deliverable: each dataset trains and tests the same pipeline, which then runs on any customer table with past purchases, an offer flag and an outcome.

## 4. Method in plain words

The method rests on one idea: compare people who got the message with near-identical people who did not, and target only those for whom the message makes a difference.

| Concept | Plain meaning |
| --- | --- |
| Randomized experiment | A coin flip decided who got the message, so the two groups differ only in the message |
| Lift | Buy rate with the message minus buy rate without it |
| Uplift | How much the message raises one particular customer's chance of buying |
| Customer types | Persuadable (buys only if messaged), Sure thing (buys anyway), Lost cause (never buys), Do-not-disturb (put off by the message) |
| Qini curve | Shows how much of the total lift you capture by messaging only the top X% the model picks; the higher above a straight line, the better the model |
| Decision rule | Send the message only when expected extra profit is greater than its cost |

**Why not an ordinary prediction model?** It finds who will buy, but many of those are Sure things, so messaging them wastes money. Uplift finds who buys **because of** the message.

### Why not message everyone? The cost of the message decides

Targeting matters in proportion to what each message costs, so Nudge treats cost per message as an input, not a fixed fact.

| Message type (Indian examples) | Real cost | Should you target? |
| --- | --- | --- |
| Reminder: "you have Rs 200 in points" | Near zero, but fatigue and opt-outs | Send to almost all; skip only Do-not-disturb customers |
| Offer: "20% off this product" | Discount paid on every redeemed order, including Sure things | Yes: Sure things take the discount for nothing |
| Credit: "Rs 50 added to your wallet" | Paid upfront for every customer messaged | Yes, strongly: only Persuadables are worth it |

- **Why X5 held back half:** without a no-message group, nobody can tell whether the message caused any purchase. The held-back group is what makes the measurement possible.
- **Even free messages have a cost:** unsubscribes, app uninstalls and annoyed customers; uplift modelling finds the customers the message puts off.
- **How the project uses this:** the money simulator runs from a free reminder up to a costly credit, showing where targeting starts to pay. This is the main business insight to present.

### Analysis plan: six comparisons

Every result in the project is one of six comparisons, each answering one question.

| # | Compare | How | Output |
| --- | --- | --- | --- |
| 1 | Message vs no-message groups, before the campaign | Group averages; standardised difference under 0.05 | Groups were alike, so later differences are caused by the message |
| 2 | Buy rate after, message vs no message | Difference with a 95% range | Overall effect (+3.3 points) and how much is wasted on people who buy anyway |
| 3 | The same difference inside segments: age, frequency, spend, points use, promo-points use, tenure | Lift per segment | Plain insights a manager can act on |
| 4 | Uplift model vs random, a simple rule, and a normal "likely buyer" model | Rank held-out customers by score; Qini curve | Proof the model finds persuadable customers better than the alternatives |
| 5 | Sending policies in money: all, none, top X% by each model, rule of thumb | Net = extra buyers x margin - customers messaged x cost, at three cost levels | The cheapest policy for each message type |
| 6 | Naive vs fair estimate where targeting was not random (Complete Journey) | Raw comparison vs matched comparison with placebo check | Why experiments matter |

## 5. System components

Nudge has nine parts; the uplift model is the core and everything else either feeds it or turns its output into a decision.

| Component | What it does | How it works |
| --- | --- | --- |
| Customer profile builder | Turns raw purchases into one row per customer | Items rolled into trips, trips into features: frequency, spend, recency, basket size, points earned and spent, promo-points use, store loyalty |
| Uplift model (core) | Scores each customer: how much contact changes their buying | Two models, one trained on contacted customers and one on the rest; uplift = predicted buy chance with contact minus without. Compared against single-model and class-transformation methods |
| Qini chart | Proves the model works | Held-out customers ranked by score; for each top X%, contacted vs not-contacted buy rates compared; curve vs random line |
| Next-best-offer | Chooses the best action per customer: none, reminder, discount or credit | One uplift estimate per offer type (Hillstrom, Starbucks); pick the action with the highest expected profit after its cost |
| Money simulator | Shows profit of any sending policy | Inputs: margin per purchase, cost per message or offer; outputs: extra buyers, cost, net profit, at reminder, offer and credit cost levels |
| Budget optimiser | Splits a fixed budget across customers and offers | Ranks every customer-offer pair by profit per rupee and fills the budget greedily; checked against an exact optimisation on a sample |
| Measurement playbook | Keeps future campaigns provable | Holdout size from a sample-size calculation, test length, a permanent small holdout, and a re-train schedule |
| Web app | Lets a marketer use the model without code | Streamlit: upload a customer list, set budget and offer costs, get who-gets-what with money impact and the Qini chart |
| AI assistant | Answers questions in plain words | Reads the model's results table and answers questions such as "why is this customer excluded?"; it explains numbers, never invents them |
| India memo | Makes it relevant to Indian companies | One page mapping the engine to Zepto, Swiggy, Tata Neu and D2C coupon, push and wallet-credit spend |

**Known limits, discussed not solved:** pull-forward (whether contact creates new purchases or only moves them earlier) and long-term discount dependence both need post-campaign history that none of the datasets include.

## 6. Validation gates

Each gate has a pass bar written before the test runs; a failed gate stops or reshapes the project.

| Gate | Question | Pass bar | Status |
| --- | --- | --- | --- |
| K1 | Was the message assigned at random? | Every balance difference under 0.05 | Passed |
| K2 | Does the message work overall? | 95% range of lift excludes zero | Passed |
| K3 | Is the purchase history usable? | Full file loads; experiment customers have history | Next |
| K4 | Does the model target better than random? | Top 50% picked captures at least 70% of the lift, and beats an age-only rule | Pending, decides go or stop |
| K5 | Does targeting make money sense? | Targeted policy beats send-to-all across the cost range | Pending |

Two gates added with the wider scope: **K6** (Hillstrom and Starbucks load cleanly, and Hillstrom's three groups are balanced) and **K7** (next-best-offer beats sending the single best offer to everyone, on held-out customers).

## 7. Results so far

**Progress at a glance (24 Oct 2026): 10 steps done, every gate passed.**

| Step | What it answered | Key result | Gate |
| --- | --- | --- | --- |
| 1 Data health | Can the X5 data be trusted? | Clean joins, 6 cleaning rules, a future-date leak found and fenced | Pass |
| 2 Profiles | How does each customer shop? | 67 measures for 400,162 customers; groups balanced on all of them | K3 pass |
| 3 First uplift model | Can we find who responds to the message? | Top 30% lift 5.6 points vs 3.3 average | K4 go |
| 4 Model selection | Which model is best, fairly? | Ensemble +27% Qini on a locked exam; top 10% respond 3.5× average | Pass |
| 5 Who to message | Does uplift beat the usual approach? | 177 vs 15 extra buyers per 10,000 vs a likely-buyer model; 3 personas | Pass |
| 6 Offer types | Reminder, discount or reward? | Biggest lift (reward) keeps least profit; free reminder gives 90% of discount value | K6 pass |
| 7 The engine | One engine for any data? | Beats both blanket policies when messages cost money; falls back safely when personalising does not pay | K7 pass |
| 8 Money simulator | Whom to contact, which channel and offer, for what budget, in rupees? | ₹20k WhatsApp budget: ₹2.44 lakh with uplift vs ₹3,300 with a likely-buyer model; a free item beats a discount; plan survives stress tests | K5 pass |
| 9 Measurement playbook | How to keep proving it works and know when to retrain? | Naive report overstates 8.6×; targeted-only retraining makes the model worse than random; recording the chance doubles retrained quality; real drift stable | K8 pass |
| 10 Contrast case | What goes wrong without a random test? | Naive report 5.6×, but 6.3× gap before the campaign; two careful methods give +10.7% and −6.5% | K9 pass |

Next: Step 11, the web app (upload a CSV, get a targeting plan in rupees).

The experiment is fair and the message works; how much it works depends strongly on who receives it.

**Fairness (K1).** The two groups match on everything measured:

| Measure | Got message | No message | Standardised difference |
| --- | --- | --- | --- |
| Average age | 46.5 | 46.4 | +0.005 |
| Days since card issued | 416 | 414 | +0.009 |
| Ever used points | 92% | 91% | +0.023 |
| Gender F / M / unknown | 37 / 17 / 46% | 37 / 17 / 46% | none |

**Overall lift (K2).** Buy rate 63.7% with the message vs 60.3% without: +3.3 points (95% range +2.9 to +3.8), about +5.5% relative.

**Lift by age.** +1.3 points for ages 14 to 25, rising steadily to +5.9 points for 65 and over. Targeting has value even with a single attribute.

**Contrast case (Complete Journey).** Where the company chose whom to target, targeted households spent 3 to 5.6 times more than others, so a naive report would claim huge returns. Fair comparisons put the true effect between about -7% and +11%, and the answer flipped with the choice of comparison group. This is why a randomized experiment is the foundation.

### Step 1 · Data health check (PASS)

**Verdict: PASS.** The three X5 files join perfectly, have almost no duplicates or junk, and their blanks carry meaning. One trap was found and fenced off: some dates fall after the experiment.

|  |  |
| --- | --- |
| **Question** | Can this data be trusted before any model touches it? |
| **Data used** | uplift\_train (200,039 rows), clients (400,162), purchases (45,786,568) |
| **How** | Six checks in one notebook (00\_data\_health.ipynb); DuckDB reads the 670 MB purchase file in chunks after a one-time conversion to Parquet |
| **What came out** | A data dictionary, six check results, the confirmed timeline, and a six-rule cleaning rulebook |
| **Run on** | 22 Oct 2026, on Vipul's laptop in VS Code |

#### How the files connect

&#91;embedded content: how the 3 X5 files connect · join on client\_id\]

Each experiment customer gets their profile from clients and four months of bills from purchases. No customer is lost in the join.

#### Data dictionary

Every column in plain words, with an illustrative example value (ids are placeholders). Money is in roubles; 10 points = 1 rouble.

| File | Column | What it means | Example |
| --- | --- | --- | --- |
| uplift\_train | client\_id | Customer ID, the key that joins all files | a1b2c3d4e5 |
| uplift\_train | treatment\_flg | 1 = got the message, 0 = did not (random) | 1 |
| uplift\_train | target | 1 = bought in the window after the message | 1 |
| clients | first\_issue\_date | When the loyalty card was issued | 2018-03-01 |
| clients | first\_redeem\_date | First time points were spent; blank = never | 2018-03-20 |
| clients | age | Age in years (has junk values, see rules) | 45 |
| clients | gender | F, M or U (unknown) | F |
| purchases | transaction\_id | Bill ID | b2c3d4e5f6 |
| purchases | transaction\_datetime | Date and time of the bill | 2018-12-01 07:12 |
| purchases | purchase\_sum | Total of the whole bill, repeated on every line | 1,007 |
| purchases | regular\_points\_received / spent | Normal loyalty points earned / used on the bill | 10 / 0 |
| purchases | express\_points\_received / spent | Promotional bonus points earned / used | 0 / 0 |
| purchases | store\_id | Store where the bill was paid | c3d4e5f6a7 |
| purchases | product\_id | Product on this line | d4e5f6a7b8 |
| purchases | product\_quantity | Units on this line (0 for some weighed items) | 2 |
| purchases | trn\_sum\_from\_iss | Amount for this product line | 80 |
| purchases | trn\_sum\_from\_red | Part of this line paid with points; blank = none | blank |

#### The six checks

All six passed; two found details that change how later steps count money and dates.

| Check | Question | How | Result | Verdict |
| --- | --- | --- | --- | --- |
| 1a Contents | What is in each file? | Count rows, list columns and types, show 3 rows | 200,039 / 400,162 / 45,786,568 rows; about 8.0M bills, about 5.7 product lines per bill | Pass |
| 1b Joins | Do the files connect? | Match every client\_id across files | 100% of experiment customers are in clients and have purchases; all 400,162 clients have purchases | Pass |
| 1c Duplicates | Any repeated rows? | Count repeated customers, exact duplicate rows, repeated bill-product pairs; check bill totals per bill | 0 repeated customers; 0 exact duplicate rows; 3 repeated bill-product pairs. purchase\_sum is the bill total repeated on each line. 28 of 8M bill IDs are shared by two customers | Pass, 2 rules |
| 1d Blanks | Are blanks errors or facts? | Blank % per column | first\_redeem\_date 8.9% blank = never redeemed; trn\_sum\_from\_red 93% blank = no points used on that line; nothing else blank | Pass |
| 1e Junk | Any impossible values? | Range checks on age, gender, quantity, amounts, dates | 1,779 impossible ages (0.4%, from -7,491 to 1,901); 46% gender U; 2.7M lines with quantity 0 (5.9%); 620 lines with bill total 0; 536 redeem dates before card issue; **redeem dates run to Nov 2019, after the experiment** | Pass, 4 rules |
| 1f Timeline | What dates does the data cover? | First and last purchase; bills per day; cards per month | History 21 Nov 2018 to 18 Mar 2019; active customers grow from 223K (Nov, partial) to 378K (Mar) a month | Pass |

**Two real-world signals in the daily chart:** a spike on 31 Dec (New Year shopping) followed by a crash on 1 Jan, and a spike on 8 Mar (Women's Day, a major holiday in Russia). The data behaves like a real grocery chain.

#### Timeline

&#91;embedded content: X5 data timeline · history cut-off 18 Mar 2019\]

The model learns only from the four months before the cut-off. The exact message date is not published; it falls after 18 Mar 2019.

#### Cleaning rulebook

Every later step applies these six rules, so the same customer always gets the same numbers.

1. **Ages outside 14–100 become blank.** 1,779 customers; dropping them would throw away good purchase data.
2. **Gender U stays as its own group.** It is 46% of customers; dropping it would halve the data.
3. **Spend is counted once per bill**, using purchase\_sum. Adding it across lines would inflate spend about 5.7 times.
4. **A bill = transaction\_id + client\_id.** Fixes 28 bill IDs shared by two customers.
5. **Product value uses the line amount, not quantity.** 5.9% of lines show quantity 0, likely weighed items.
6. **Nothing dated after 18 Mar 2019 is used as an input.** "Ever redeemed" counts only redeems on or before that date. Without this, the model would learn from the future.

#### What Step 1 proves

- **The data is real and complete.** Every experiment customer has a profile and four months of bills, so no one drops out of the analysis.
- **The numbers mean what we think.** The bill total sits on every line and blanks are facts, so later spend and points figures are correct.
- **Time is fenced.** Inputs stop at 18 Mar 2019, so the model never sees what happened after the message.

**Interview question this prepares:** *"How did you make sure your model was not cheating?"*

> Before modelling, I checked every date column against the experiment timeline. The first-redeem date ran to November 2019, months after the message. Using it raw would leak the future into the model. I capped every input at the last day of purchase history, 18 March 2019.

### Step 2 · Customer profiles (PASS)

**Goal:** turn 45.8M purchase lines into one row per customer with 67 measures, using only data up to 18 Mar 2019. The uplift model learns from these rows to tell persuadable customers from the rest. Run on 22 Oct 2026 in about one minute; K3 passed on all three checks.

|  |  |
| --- | --- |
| **Question** | How does each customer shop, in numbers a model can use? |
| **Data used** | purchases + clients, with all six cleaning rules |
| **How** | One DuckDB pass builds a bill table, then helper tables (visit gaps, product repeats, store use), then all measures; saved as customer\_profiles.parquet (notebook 02\_profiles.ipynb) |
| **What comes out** | A 400,162 × 67 profile table, a balance chart across all measures, and a portrait of the typical customer |

&#91;embedded content: Step 2 pipeline · purchase lines to customer profiles\]

The profile table feeds every later step; the K3 gate stops the project if it is incomplete, leaks the future, or shows unbalanced groups.

#### How it was built, stage by stage

Each stage answers one question; together they turn raw bill lines into a fair, comparable description of every customer.

| Stage | What we did | Why | Size and time |
| --- | --- | --- | --- |
| 1. Bill table | Collapsed product lines into one row per bill (transaction + customer). Bill-level fields (total, points, store, time) taken once; line amounts summed. Added days\_ago = days before the cut-off | Rules 3 and 4: counting the bill total on every line would inflate spend about 5.7 times | 45.8M lines to 8,045,229 bills; 4 seconds |
| 2. Helper tables | Gaps between shopping days; how often each product repeats; bills per store | Rhythm, habit and store loyalty need these counts first | Part of 55 seconds |
| 3. Time windows | Counted bills and spend over the last 7, 14, 30 and 60 days and in total | Recent behaviour predicts better than lifetime totals; several windows show direction | Part of 55 seconds |
| 4. Ratios | Overdue ratio, 30-day trends, bills per week, spend per day, shares of bills or value | Ratios let a light shopper and a heavy shopper be compared fairly | Instant |
| 5. Card and profile | Clean age, card age, redeem history capped at the cut-off | Rules 1 and 6 | Instant |
| 6. Save | One table for all 400,162 customers, including the half without labels | Every later step loads it instantly; the unlabelled half can be scored later | customer\_profiles.parquet |
| 7. K3 checks | Completeness, no future data, balance on every measure | A model on a broken or leaky table gives confident wrong answers | Instant |

**Reading one profile: one real customer (id withheld).** 32 bills in four months, 2.0 a week, 5 stores, average bill 306 roubles, last visit 1 day before the cut-off. Usual gap between visits is about 3.5 days, so the overdue ratio is 0.28: a loyal regular, right on rhythm. Customers like this may buy anyway, which is exactly what the uplift model must learn to spot.

**Standardised difference, in one line:** the gap between two group averages divided by how spread out the measure is. Under 0.05 means the groups are practically identical.

#### The 67 measures, by industry-standard group

| Group | Standard name | Measures | Why it matters |
| --- | --- | --- | --- |
| A | Recency / lifecycle | Days since last bill, days since first bill, active span | The R of RFM; lapsing customers may need a nudge |
| B | Frequency and purchase rhythm | Bills over 7, 14, 30, 60 days and total; active days; bills per week; gap between visits (mean, spread, max, regularity) | Inputs of standard repeat-purchase models (BG/NBD); regulars may buy anyway |
| C | Monetary | Spend over 7, 14, 30, 60 days and total; mean, median, max, min bill; bill spread; spend per day | The M of RFM |
| D | Velocity / trend | Spend and visits, last 30 days vs the 30 before; share of spend in the last 30 days | Catches customers who are slowing down |
| E | Basket | Lines and units per bill, value per line, distinct products, repeat-product share, top-product share | Habit vs exploration |
| F | Loyalty economy | Regular points earned and spent, per bill and last 30 days; share of bills using points; share of value paid with points; net points flow | Engagement with the loyalty programme |
| G | Promo sensitivity | Express (bonus) points earned and spent, total and last 30 days; share of bills with them; spent per bill | Strongest signal in the X5 competition's 2nd-place solution |
| H | Store loyalty | Number of stores, share of bills at the main store | Habitual vs convenience shopper |
| I | Time habits | Weekend, morning, evening share; mean hour; share of spend in holiday weeks | Lifestyle |
| J | Card / profile | Card age, card issued in history window, redeemed by cut-off, days from card to first redeem, days since first redeem, age, age missing, gender | Lifecycle stage |

**Two measures of our own:**

- **Overdue ratio** = days since last visit ÷ the customer's usual gap. A weekly shopper away 14 days scores 2.0 (at risk); a monthly shopper away 14 days scores 0.5 (normal). Raw recency cannot tell them apart.
- **Leak-safe redeem history.** The 2nd-place solution fed the raw first-redeem date, which runs to Nov 2019, into its model. We cap it at the cut-off.

**Deliberately left out, and why:**

- **Product categories** (own brand, fresh, alcohol share): our files hold only product IDs. The original competition had a separate products file; it is a later add-on if we can get it.
- **Channel and response history** (opens, clicks, past campaigns): X5 did not release it.

#### K3 gate: results

| Check | Test | Pass mark | Result | Verdict |
| --- | --- | --- | --- | --- |
| Complete | Every experiment customer has a profile; blanks only where they mean something | 200,039 of 200,039 | 200,039 profiled, 0 missing. Blanks: 20% no redeem by cut-off, 13% no trend (no bills in the earlier window), 2% no visit gap (one shopping day), 0.4% no age | Pass |
| No future data | Latest bill used and every redeem date on or before the cut-off | Latest date on 18 Mar 2019 or earlier | Latest bill 18 Mar 2019, 23:40; earliest redeem gap 0 days = redeemed on the cut-off day itself | Pass |
| Balanced | Message and no-message groups compared on all 66 numeric measures | Every standardised difference under 0.05 | 0 of 66 over the mark; largest 0.0125 (card issued in history window), four times under | Pass, strong |

&#91;image: Balance on all 66 measures: every dot sits close to zero\]

*Balance chart from the notebook: each dot is one measure. All 66 sit within ±0.013 of zero, far inside the ±0.05 dashed lines. The random split holds on rich behaviour, not just age and gender.*

#### What a typical experiment customer looks like

| Measure | Low (10th pct) | Typical (median) | High (90th pct) |
| --- | --- | --- | --- |
| Days since last visit | 0 | 4 | 15 |
| Bills in 4 months | 4 | 15 | 42 |
| Bills per week | 0.5 | 1.2 | 3.2 |
| Total spend (roubles) | 1,556 | 6,102 | 18,287 |
| Average bill (roubles) | 179 | 394 | 926 |
| Products per bill | 2.8 | 5.5 | 10.9 |
| Stores used | 1 | 2 | 5 |
| Overdue ratio | 0.00 | 0.47 | 1.79 |
| Card age (days) | 101 | 488 | 655 |
| Age | 26 | 45 | 68 |

#### Four findings

1. **Every experiment customer was recently active.** Days since last visit run 0 to 22, median 4. X5 messaged active shoppers, so the question is who can be nudged to buy more or sooner, not who can be won back.
2. **The leak fix mattered.** 80% had redeemed by the cut-off; with future dates it would read 91%. About 11% of customers would have carried future information into the model.
3. **Promo points are rare.** Bonus points were earned on 0.09% of bills and spent on 2%. A strong signal for a few customers, silent for most.
4. **Some cards look shared or business-like.** Up to 320 bills in four months, 95 stores, 77 bills a week. Tree models tolerate them; Step 4 will flag them.

#### What Step 2 proves

- **The model has a rich, clean input:** 67 measures for every customer, built only from the past.
- **The experiment is fair on everything we can measure,** so any difference after the message is caused by the message.
- **The target group is active shoppers,** which shapes what a message can realistically do.

**Interview question this prepares:** *"What features did you build, and why those?"*

> I grouped 67 measures into ten standard lenses: recency, frequency and rhythm, spend, trend, basket, loyalty points, promo points, store loyalty, time habits and card lifecycle. I added an overdue ratio, which compares each customer with their own rhythm instead of a fixed cut-off. Before modelling, I checked that the message and no-message groups matched on all 67; none differed by more than 0.013 standard deviations.

Sources: [X5 2nd-place solution](https://nbviewer.jupyter.org/github/kirrlix1994/Retail_hero/blob/master/Retail_hero_contest_2nd_place_solution.ipynb) · [scikit-uplift Hall of Fame](https://www.uplift-modeling.com/en/latest/hall_of_fame.html)

### Step 3 · Quick uplift model and first Qini chart (PASS: GO)

**Goal:** prove, on customers the model has never seen, that ranking people by predicted uplift finds more extra buyers than picking at random. This is the project's go-or-stop test (K4).

|  |  |
| --- | --- |
| **Question** | Can we predict who buys because of the message, not just who buys? |
| **Data used** | customer\_profiles.parquet, the 200,039 experiment customers with message flag and outcome |
| **How** | Split 70/30, train two standard uplift methods on gradient-boosted trees, score the 30% test half, draw the Qini chart and decile table (notebook 03\_uplift\_quick.ipynb) |
| **What comes out** | Qini chart, uplift by decile, uplift in the top 30%, the measures that drive uplift, and a go or stop verdict |

&#91;embedded content: Step 3 flow · profiles to the K4 go-or-stop decision\]

The test half is locked away until scoring, so the result shows how the model would do on new customers.

#### Start here: the four kinds of customers

&#91;embedded content: the four kinds of customers · why uplift beats 'likely buyer'\]

We can never watch the same person both with and without the message, so nobody comes labelled "persuadable". The uplift model's whole job is to estimate which box each customer sits in. A normal "likely buyer" model cannot do this: it happily picks sure things, who buy anyway.

#### The ideas, in plain words

| Idea | Plain meaning | Example |
| --- | --- | --- |
| Uplift | Chance of buying with the message minus chance without it, for one customer | 70% with, 62% without: uplift +8 points |
| T-learner (two-model) | Model A learns buying among messaged customers, model B among the rest; uplift = A minus B | A says 70%, B says 62%: +8 points |
| Class transformation | Relabel each customer: 1 if messaged and bought, or not messaged and did not buy; one model; uplift = 2 × its score − 1. Valid because the split was 50/50 | The method of the X5 competition's 2nd-place solution |
| Gradient-boosted trees | Many small decision trees, each fixing the last one's errors; handle blanks and outliers natively | Standard choice for tabular data |
| Qini curve | Sort test customers by predicted uplift; for each top slice, count the real extra buyers. Random targeting is a straight line | A curve high above the line = targeting works |
| Uplift at top 30% | Real lift (buy rate with message minus without) among the 30% the model ranks highest | Compare with the 3.3-point average |
| Decile table | Ten ranked groups, real lift measured in each | Should fall from group 1 to group 10 |

#### Why these choices

- **Two methods, not one:** if both agree, the signal is real; if only one works, we learn something about the data.
- **Gradient-boosted trees (scikit-learn):** the 67 measures have blanks and extreme values; trees handle both without extra cleaning, and train in seconds on 140,000 rows.
- **Qini, not accuracy:** the business question is how many extra buyers each message brings. Accuracy at predicting buyers rewards finding people who would buy anyway.
- **Our own Qini code:** a few transparent lines, cross-checked against the scikit-uplift library, so every number can be explained in an interview.

#### K4 gate: go or stop

| Check | Pass mark |
| --- | --- |
| Qini curve above random | Area between curve and random line above zero, with its 95% bootstrap range also above zero |
| Top 30% is richer | Real lift in the top 30% at least 1.5 times the 3.3-point average (5 points or more) |
| Ranking holds | Real lift falls from the top decile to the bottom decile |

**If K4 fails:** we stop modelling, write up why targeting adds nothing here, and switch the project weight to the offer-type datasets.

#### Results: K4 passed, the project is a GO

Run on 22 Oct 2026. Training took 11 seconds; the split kept the same 3.32-point lift in both halves (140,027 train, 60,012 test).

| Measure | T-learner | Class transformation | What it means |
| --- | --- | --- | --- |
| Qini area above random | 103.9 | 102.9 | Both clearly beat random |
| 95% range | 37 to 168 | 44 to 176 | Stays above zero: not luck |
| Real lift, top 10% | 6.2 pts | **8.7 pts** | Class transformation sharper at the very top |
| Real lift, top 30% | 5.2 pts | **5.6 pts** | Both clear the 5-point bar |
| Agreement between the two | rank correlation 0.43 |  | Real signal, but noisy |

The scikit-uplift library reproduced our top-30% numbers exactly (5.17 and 5.61), so our own code is correct.

&#91;image: Step 3 Qini curve and lift by decile\]

**How to read the Qini chart (left), with real numbers from the 60,012 test customers:**

- Message everyone: about **1,000 extra buyers** (where the curves end).
- Message a random 30%: about **300** extra buyers (the dashed line).
- Message the model's top 30%: about **465** extra buyers, **55% more** from the same number of messages.

**How to read the decile bars (right):** each bar is the real lift in one tenth of customers, ranked by predicted uplift. Group 1 shows 6.1 points, nearly double the 3.3 average; groups 9 and 10 show about 1.8. The slope is downward but bumpy, a first sign of noise.

#### Who is persuadable?

| Median of | Persuadable (top 30%) | Low uplift (bottom 30%) |
| --- | --- | --- |
| Bills in 4 months | 11 | 18 |
| Total spend (roubles) | 4,042 | 7,606 |
| Age | 50 | 41 |
| Card age (days) | 419 | 543 |
| Days since last visit | 6 | 3 |
| Stores used | 2 | 3 |

**In plain words: persuadables are lighter, older, less frequent shoppers.** Heavy regulars are mostly sure things. A likely-buyer model would have targeted exactly those regulars and wasted the budget.

&#91;image: Top 15 measures for spotting uplift\]

The strongest drivers: points earned in the last 30 days, age, bonus points spent per bill (promo sensitivity, as the competition winners found), basket concentration, and days active.

#### K4 gate results

| Check | Pass mark | Result | Verdict |
| --- | --- | --- | --- |
| Qini beats random | 95% range above zero | 37 to 168 | Pass |
| Top 30% is richer | 5 points or more | 5.2 (T-learner) | Pass |
| Ranking holds | Top 3 deciles above bottom 3 | 5.1 vs 2.1 points | Pass |

**Why we did not stop here:** the two models nearly tied, agreed only 0.43 on who is persuadable, and the decile bars were bumpy. One 70/30 split is too noisy to crown a winner, so Step 4 runs a proper model selection.

**Interview question this prepares:** *"Why build an uplift model instead of predicting who will buy?"*

> A likely-buyer model ranks heavy regulars first, but they buy anyway, so messaging them wastes budget. The uplift model ranks by the change the message causes. In my data the persuadable customers were lighter, older shoppers with about 40% fewer bills than the low-uplift group.

### Step 4 · Model selection: find the best model, fairly (PASS)

**Result: an ensemble of three uplift methods beats Step 3's model by 27% on customers it never saw, and its top 10% respond 3.5 times more than average.**

|  |  |
| --- | --- |
| **Question** | Which uplift model ranks persuadable customers best, and can we trust that choice? |
| **Data used** | The 67-measure profiles of all 200,039 experiment customers |
| **How** | Locked 20% away; compared 8 models with 5-fold cross-validation on the rest; re-tested on 2 more random splits; tuned the top two; judged the champion on the locked 20% (notebook 04\_model\_selection.ipynb) |
| **What came out** | A champion model, an honest measure of its gain, and uplift scores for all 400,162 customers |
| **Run on** | 22–23 Oct 2026: search by Claude in the cloud, final notebook run by Vipul in VS Code with identical results |

&#91;embedded content: Step 4 testing design · choose on 80%, judge on a locked 20%\]

The locked 20% is the only fair judge: everything on the top row helped choose the model, so it cannot also grade it.

#### Five changes from Step 3, and why each helped

| Change | Step 3 | Step 4 | Why it helped |
| --- | --- | --- | --- |
| 1. Smarter uplift methods | T-learner, class transformation | S-, X- and DR-learners | X and DR learn each customer's gap directly instead of subtracting two noisy predictions; subtracting doubles the noise |
| 2. Combine models | One model | Average rank of S, X and DR | Each method makes different mistakes; averaging cancels some of them |
| 3. Stronger tree engine | scikit-learn trees | LightGBM, heavier regularisation | The signal is tiny (3.3 points), so every tree rule must cover 400+ customers and cannot chase noise; this alone lifted the T-learner's Qini from 0.0081 to 0.0110 |
| 4. Fairer testing | One 70/30 split | Locked 20% + 5-fold cross-validation + 2 repeat splits | One split can flatter a lucky model; averages over many tests do not |
| 5. Honest tuning | None | 22 settings per model, checked on fresh splits | Tuning looked better at first but did not survive fresh splits, so defaults were kept |

#### The contenders, in one line each

| Method | How it estimates uplift | Everyday analogy |
| --- | --- | --- |
| T-learner | Two models (messaged, not messaged); subtract | Two fortune-tellers, one per world |
| Class transformation | One model on a relabelled target | A trick that works because the coin flip was 50/50 |
| S-learner | One model with "was messaged" as an input; flip it on and off | One fortune-teller asked the same question twice |
| X-learner | Guess each customer's personal gap, then learn those gaps | Learning from each person's missed alternative |
| DR-learner | A corrected per-customer estimate that stays right if one part is wrong | A second opinion that checks the first |
| Ensemble | Average rank of S, X and DR | A panel of three judges |

#### Cross-validation: 8 models, 5 folds each

| Model | Qini (mean ± fold spread) | Real lift, top 10% | Real lift, top 30% |
| --- | --- | --- | --- |
| **Ensemble S+X+DR** | **0.0144 ± 0.0027** | 9.8 pts | 6.3 pts |
| X-learner | 0.0141 ± 0.0027 | 9.9 pts | 6.2 pts |
| S-learner | 0.0139 ± 0.0041 | 10.4 pts | 6.1 pts |
| DR-learner | 0.0132 ± 0.0018 | 9.9 pts | 6.4 pts |
| T-learner (LightGBM) | 0.0110 ± 0.0036 | 9.2 pts | 5.8 pts |
| Class transformation (Step 3) | 0.0109 ± 0.0016 | 8.2 pts | 5.9 pts |
| Class transformation (LightGBM) | 0.0106 ± 0.0020 | 8.5 pts | 5.8 pts |
| T-learner (Step 3) | 0.0081 ± 0.0055 | 7.9 pts | 5.3 pts |

&#91;image: Cross-validated model comparison\]

#### Does the ranking hold? Repeat splits and tuning

| Model | Mean Qini over 3 random splits |
| --- | --- |
| **Ensemble (default settings)** | **0.0146** |
| X-learner, default | 0.0145 |
| X-learner, tuned | 0.0140 |
| S-learner, tuned | 0.0139 |
| DR-learner, default | 0.0137 |
| S-learner, default | 0.0137 |

**Lesson: tuning chased noise.** Tuned settings won on the splits they were tuned on, then lost to defaults on fresh splits. Keeping defaults is simpler and more honest.

#### Final exam on the locked 20%

| Measure | Step 3 model | Champion | Change |
| --- | --- | --- | --- |
| Qini | 0.0114 | **0.0144** | **+27%** |
| Qini 95% range | 0.006 to 0.018 | 0.008 to 0.020 | Both above zero |
| Real lift, top 10% | 8.4 pts | **11.7 pts** | +3.3 pts |
| Real lift, top 30% | 5.6 pts | 6.1 pts | +0.5 pts |

&#91;image: Final exam: Qini curve and lift by decile\]

- **Qini curve (left):** the champion climbs much faster in the first 20%, about 350 extra buyers against 270. Both end at about 670, since messaging everyone gives the same total.
- **Decile bars (right):** group 1 at 11.7 points and group 2 at 6.0 stand far above the 3.3 average. Groups 3 to 10 bounce between −1.8 and 4.8: each holds about 2,000 customers per side, so any single bar carries about ±3 points of noise.

#### What it means for a business

| Message only the top | Share of all extra buyers kept | Messages saved |
| --- | --- | --- |
| 10% | 35% | 90% |
| **20%** | **53%** | **80%** |
| 30% | 54% | 70% |
| 50% | 65% | 50% |

**Rule of thumb: message the top 20%.** That keeps over half the extra sales for a fifth of the messages; going to 30% adds almost nothing.

#### Honest limits

- **Groups, not individuals.** Trained on two different halves of the data, the same recipe agrees on only about 60% of its top-30% customers. Uplift for one person is uncertain; uplift for a group is reliable.
- **The middle is flat.** Below the top 20% the model cannot rank people meaningfully, which is why the rule stops there.

#### What Step 4 proves

- The champion was chosen fairly and confirmed on untouched data: the 27% gain is real, not a lucky split.
- The value sits in the top fifth of customers, which makes a clear, defensible targeting rule.
- Every customer now has an uplift score, ready for the money simulator.

**Interview question this prepares:** *"How did you choose your model, and how do you know it is not overfit?"*

> I locked 20% of customers away first. On the other 80% I compared seven uplift methods with five-fold cross-validation and repeated it on two more random splits. An ensemble of S-, X- and DR-learners won consistently. Tuning helped only on the splits it was tuned on, so I kept defaults. On the locked 20% the champion beat the baseline by 27%, and its top 10% responded 3.5 times more than average.

### Step 5 · Who to message, and why uplift beats the obvious approach (PASS)

**Result: targeting the top 20% by uplift creates 177 extra buyers per 10,000 customers. The industry-standard likely-buyer model creates 15, worse than picking at random.**

|  |  |
| --- | --- |
| **Question** | Is uplift really better than "target likely buyers", and what does a marketer do with it? |
| **Data used** | The locked 20% from Step 4 (40,008 customers) for every comparison; the 80% for building |
| **How** | A: head-to-head of four targeting methods. B: a 3-question uplift tree. C: personas from the tree (notebook 05\_who\_to\_message.ipynb) |
| **What came out** | The trap chart, 5 plain-English rules, 3 personas with actions |
| **Run on** | 23 Oct 2026, identical results on Vipul's laptop and in the cloud |

#### Part A: the head-to-head

Four ways to choose which 20% of customers get the message:

| Method | How it picks | Buy rate of those picked | Real lift | Extra buyers per 10,000 |
| --- | --- | --- | --- | --- |
| Likely-buyer model | Highest chance of buying (LightGBM on messaged customers) | **93%** | 0.75 pts | **15** |
| Heavy-shoppers rule | Most bills in the last 30 days | 91% | 0.97 pts | 19 |
| Random | Coin flip | 65% | 3.8 pts | 77 |
| **Uplift champion** | Biggest change caused by the message | 52% | **8.9 pts** | **177** |

&#91;image: The trap: buy rate vs extra buyers created\]

**The trap, in one line:** the likely-buyer model picks people who already buy 93% of the time, so the message has no room to change anything. It looks brilliant on a dashboard and creates almost nothing. The uplift model looks worse on buy rate and creates 12 times more extra buyers.

**How sure:** uplift beats likely-buyer by **+161 extra buyers per 10,000** (95% range +110 to +211).

&#91;image: Extra buyers at every budget\]

| Message the top | Likely-buyer | Random | Uplift |
| --- | --- | --- | --- |
| 10% | 3 | 28 | **117** |
| 20% | 15 | 77 | **177** |
| 30% | 39 | 119 | **182** |
| 50% | 115 | 165 | **218** |

Uplift wins at every budget, and by the most at small budgets, where companies usually operate.

#### Part B: rules a marketer can use without a model

&#91;embedded content: uplift tree · 5 segments, real lift measured on the locked 20%\]

**How the tree works:** in a 50/50 experiment, the value 2 × bought × (+1 if messaged, −1 if not) averages to the true uplift in any group. An ordinary regression tree on it becomes an uplift tree: each split separates customers who respond differently to the message.

| # | Rule in plain words | Share | Real lift (95% range) | Tier |
| --- | --- | --- | --- | --- |
| 1 | Spent bonus points in the last 30 days | 6% | **8.4 pts** (4.5 to 12.4) | High |
| 2 | No recent bonus points, over 50, card under \~11 months | 11% | **5.2 pts** (2.4 to 8.1) | High |
| 3 | No recent bonus points, over 50, older card | 28% | 2.9 pts (1.2 to 4.7) | Medium |
| 4 | No recent bonus points, 50 or under, shops less often than every 3.5 days | 47% | 2.8 pts (1.3 to 4.2) | Medium |
| 5 | No recent bonus points, 50 or under, shops every 3.5 days or more often | 9% | **1.2 pts** (−1.0 to 3.3) | Low |

**Why only 3 questions deep? Deeper trees learn noise.**

| Tree size | Segments | Agreement, predicted vs real lift |
| --- | --- | --- |
| 3 deep | 5 | **1.00** (perfect order) |
| 4 deep | 10 | 0.53 |
| 4 deep, smaller groups | 11 | 0.46 |
| 5 deep | 16 | 0.19 (mostly noise) |

#### Part C: personas and actions

| Persona | Who they are (medians) | Share | Real lift | Action |
| --- | --- | --- | --- | --- |
| **High: the nudgeable** | Promo-point users, or older new members: age 59, card \~6 months, 13 bills in 4 months | 17% | **6.4 pts** | Message first, even with costly offers |
| **Medium: the average shopper** | Age 44, 14 bills, card \~1.5 years | 74% | 2.9 pts | Message only if the message is cheap |
| **Low: the loyal regular** | Age 35, 44 bills, 14,331 roubles in 4 months | 9% | 1.2 pts | Do not spend: they buy anyway |

**Efficiency vs volume:** Medium creates more extra buyers in total (215 per 10,000) than High (107) because it is four times bigger. High is the most efficient per message; Medium has the volume. Which wins depends on the cost of each message, the question the money simulator answers.

**Rules vs model:** at the same 17% coverage, the High-tier rules create 107 extra buyers per 10,000 against 161 for the full model. The rules keep **67% of the gain** with no model at all.

#### Is the model optimised, and are the results good?

| Check | Evidence | Verdict |
| --- | --- | --- |
| Methods compared | 7 uplift methods plus an ensemble | Thorough |
| Fair testing | Cross-validation, 2 repeat splits, locked final exam | Stronger than most published projects |
| Tuning | 22 settings per model; did not survive fresh splits | Defaults kept, deliberately |
| Top 10% vs average | 11.7 vs 3.3 pts (3.5×) | Strong |
| Uplift vs random at 20% | 177 vs 77 extra buyers (2.3×) | Strong |
| Uplift vs likely-buyer at 20% | 177 vs 15 (about 12×), range clearly above zero | Very strong |

**Why stop optimising here:** the data has a noise ceiling (average effect 3.3 points, flat middle deciles, \~60% overlap of the top 30% between retrains). More modelling might add 5–10% on Qini; the next steps add whole new capabilities. The one change still worth trying later is product-category measures, if X5's products file can be found.

**Honest limits:** one campaign and one message type; individual scores are rough while group decisions are reliable; the thresholds (age 50, 3.5-day gap) belong to a Russian grocer and must be re-learned on Indian data. The method transfers, the numbers do not.

**Interview question this prepares:** *"Why not just send offers to your best customers?"*

> Because they buy anyway. I tested it: targeting the top 20% by likely-to-buy created 15 extra buyers per 10,000 customers, worse than random at 77. Targeting by uplift created 177. Best customers look great on a dashboard, but the message changes almost nothing for them.

### Step 6 · Offer types: reminder vs discount vs reward (PASS)

**Goal:** X5 tested one message. Real companies choose between a free reminder, a discount and a reward. Step 6 measures what each offer type adds, what it costs, and whether the best offer differs by customer, using two more randomized experiments.

|  |  |
| --- | --- |
| **Question** | Which offer type creates the most value after its cost, and for whom? |
| **Data used** | Starbucks rewards (simulated by Starbucks for Udacity: 17,000 customers, 10 offers, 6 waves, 306,534 events) and Hillstrom email test (real: 64,000 customers, men's email vs women's email vs no email) |
| **How** | Turn each dataset into a clean experiment, check it is random (K6), measure lift and spend per offer, subtract the offer's cost, and compare across customer groups (notebook 06\_offer\_types.ipynb) |
| **What comes out** | An offer ladder with net value per offer, a who-prefers-what table, and inputs for the next-best-offer engine (Step 7) |

#### Mapping to the Indian offer ladder

| Indian offer | Cost to the company | Starbucks equivalent | Hillstrom equivalent |
| --- | --- | --- | --- |
| Reminder (push, SMS, WhatsApp) | Near zero | Informational offer (reward 0) | Either email (cost of sending only) |
| Discount (% or rupees off) | Paid only when used | Discount offers (spend 7–20, get 2–5 back) | None |
| Reward or credit (cashback, free item) | Paid only when used, larger | Buy-one-get-one (spend 5–10, get 5–10 back) | None |

#### How the Starbucks data becomes an experiment

&#91;embedded content: Starbucks offer waves · how each wave becomes an experiment\]

In each of the 6 waves, every customer is randomly given one of 10 offers or nothing. Each customer-wave becomes one row: 17,000 × 6 = 102,000 rows. The outcome is buying and spend in the next 72 hours, the shortest gap between waves, so waves never overlap.

**First look (confirmed in the notebook):** offers are split 30% buy-one-get-one, 30% discount, 15% informational, 25% none, the same in every wave; average age (62.6) and income (about 65,400) match across all four groups, so it looks random. Buying within 72 hours: 43% with no offer, 55% informational, 57% discount, 60% buy-one-get-one.

#### The plan, part by part

| Part | Data | What we do | Why |
| --- | --- | --- | --- |
| A1 | Starbucks | Build the customer-wave table, check balance on age, income, membership length, gender | Proves the comparison is fair (K6) |
| A2 | Starbucks | Lift in buying and spend per offer type and per each of the 10 offers, with 95% ranges | Which offer moves people most |
| A3 | Starbucks | Net value = extra spend minus reward actually paid | A big lift can still lose money |
| A4 | Starbucks | Lift per offer type by age, income and membership length | Does the best offer change by customer? |
| B1 | Hillstrom | Balance check across the three groups | K6 for real data |
| B2 | Hillstrom | Lift in visits, purchases and spend per email | Real-world effect sizes |
| B3 | Hillstrom | Which customers respond to which email (past men's or women's buyers, recency, spend history) | Real evidence that the right message depends on the customer |

#### K6 gate

| Check | Pass mark |
| --- | --- |
| Random assignment | Every pre-offer measure balanced across groups (standardised difference under 0.05), in both datasets |
| Real effect | At least one offer type lifts buying with a 95% range above zero |
| Heterogeneity | The best offer type differs for at least one large customer group |

**Honest limits:** Starbucks data is simulated (labelled as such everywhere); Hillstrom is real but from US e-commerce in 2008. They teach the method and the shape of offer economics; Indian numbers must come from an Indian test.

#### Results: K6 passed (run 23 Oct 2026)

**Headline: the most generous offer is the least profitable, and the best offer depends on the customer.**

| K6 check | Result | Verdict |
| --- | --- | --- |
| Starbucks is random | Largest gap 0.0095 on age, income, membership, gender, missing profile | Pass |
| Hillstrom is random | Largest gap 0.0137 on recency, past spend, past purchases, area, channel | Pass |
| A real effect | Every offer type and both emails lift buying, 95% ranges above zero | Pass |
| Best offer differs by customer | Yes in both datasets | Pass |

#### Starbucks: lift is not profit

| Offer type | Extra buyers within 72h | Extra spend | Reward paid | Net value per customer offered |
| --- | --- | --- | --- | --- |
| Reminder (informational) | +12.5 pts | 3.71 | 0.00 | 3.71 |
| Discount | +13.8 pts | 5.04 | 0.90 | **4.13** (best) |
| Buy-one-get-one | **+17.2 pts** (biggest) | 5.82 | 2.68 | 3.14 (worst) |

Baseline with no offer: 42.9% buy within 72 hours, average spend 7.58.

&#91;image: Offer types: lift, cost and net value\]

- **Buy-one-get-one moves the most people but gives away 2.68 per customer,** so it keeps the least.
- **A free reminder delivers 90% of the discount's net value at zero cost.** For many customers, a reminder is enough.

#### Starbucks: every offer, ranked by net value

| Offer (spend / reward / days) | Type | Sent on social media | Extra buyers | Net value |
| --- | --- | --- | --- | --- |
| Spend 10, get 2, 10 days | Discount | Yes | +22.1 pts | **7.35** |
| Spend 7, get 3, 7 days | Discount | Yes | +21.0 pts | 5.72 |
| Spend 5, get 5, 5 days | Buy-one-get-one | Yes | +20.3 pts | 4.92 |
| Reminder, 3 days | Informational | Yes | +16.7 pts | 4.68 |
| Spend 10, get 10, 5 days | Buy-one-get-one | Yes | +21.4 pts | 3.30 |
| Spend 10, get 10, 7 days | Buy-one-get-one | Yes | +18.2 pts | 2.82 |
| Reminder, 4 days | Informational | No | +8.3 pts | 2.73 |
| Spend 10, get 2, 7 days | Discount | No | +8.0 pts | 2.54 |
| Spend 5, get 5, 7 days | Buy-one-get-one | No | +8.9 pts | 1.54 |
| Spend 20, get 5, 10 days | Discount | No | +4.3 pts | 0.96 |

&#91;image: Net value of each offer\]

**Two design lessons:** a small reward with a reachable target wins (spend 10, get 2 beats spend 10, get 10), and **the channel matters as much as the offer**: every offer sent on social media nets 2.8 to 7.4, every offer without it nets 1.0 to 2.7.

#### Starbucks: the best offer depends on the customer

&#91;image: Net value by customer group and offer type\]

| Customer group | Share | Best offer | Why it matters |
| --- | --- | --- | --- |
| New members (under 1 year) | 51% | Reminder | Nothing earns much; do not pay rewards to them |
| Members 1–2 years | 20% | **Discount (7.9 net)** | The most valuable group to target |
| Members 2+ years | 29% | Discount |  |
| Income 75k+ | 26% | Discount (6.6) |  |
| Income under 50k | 24% | Reminder | Rewards do not pay back |
| Age under 35 | 14% | Reminder |  |
| Missing profile | 13% | Almost nothing works (under 1.0) | Candidates for no offer at all |

#### Hillstrom (real data): the right message depends on past behaviour

| Email | Extra visits | Extra purchases | Extra spend per customer |
| --- | --- | --- | --- |
| Men's email | **+7.7 pts** (7.0 to 8.3) | +0.68 pts (0.50 to 0.86) | **+0.77** (0.49 to 1.06) |
| Women's email | +4.5 pts (3.9 to 5.2) | +0.31 pts (0.15 to 0.47) | +0.42 (0.17 to 0.68) |

Baseline with no email: 10.6% visit, 0.57% buy, 0.65 spend per customer.

&#91;image: Visit lift by past buyer type\]

| Past buyer type | Share | Men's email, extra visits | Women's email, extra visits | Better email |
| --- | --- | --- | --- | --- |
| Bought both | 10% | **+13.4 pts** | +7.1 pts | Men's |
| Men's items only | 45% | +6.9 pts | **+1.1 pts** (almost nothing) | Men's |
| Women's items only | 45% | +7.1 pts | +7.4 pts | Women's (on spend) |

**Lesson:** the women's email barely moves men's-only buyers, so sending it to them wastes the send. Matching the message to past behaviour is real money.

#### What Step 6 proves

- **Lift is not profit.** The offer that moves the most people (buy-one-get-one) keeps the least once its reward is paid.
- **A free reminder is often enough,** delivering 90% of a discount's value; costly rewards should be reserved for groups where they pay back.
- **One size does not fit all,** in simulated and real data alike: this is the case for a next-best-offer engine.

**Interview question this prepares:** *"How would you decide between a discount and a reminder?"*

> By net value, not response rate. In the Starbucks test, buy-one-get-one lifted buying by 17 points against 12 for a free reminder, but after paying the reward it kept 3.14 per customer against 3.71. Discounts won overall, yet for new members a reminder was best. So I would let a model choose the offer per customer, ranked by value after cost.

### Step 7 · The Nudge engine: one engine, any data (PASS)

**Goal:** give every customer the one option (no offer, reminder, discount, buy-one-get-one) with the highest predicted net value, and prove it beats sending everyone the same thing.

#### What we are really building: an engine, not one model

A trained model only knows the customers it learned from: one built on Russian grocery shoppers knows nothing about Indian fintech users. What transfers is the **engine**: the same code and steps, retrained on each company's own customers and its own randomized test. Credit scoring works the same way: one method, retrained by every bank.

| Dataset | Business question | Options | Value maximised |
| --- | --- | --- | --- |
| X5 (real) | Whom to contact? | message / nothing | bought, minus the message cost |
| Starbucks (simulated) | Which offer? | 10 offers / nothing | spend minus reward paid |
| Hillstrom (real) | Which message? | men's / women's email / nothing | spend |

**Standard input (any company):** one row per customer contact with features known before the contact, the option given at random, the outcome value, and optionally a cost per option and a customer id. The engine lives in `nudge_engine.py`; notebook `07_engine.ipynb` runs it unchanged on all three datasets.

**Two files, two jobs.** The engine is deliberately split from the notebook so it can be reused on any company's data.

- `nudge_engine.py` is the machine: five reusable tools (fairness check, average effects, the engine that learns and recommends, a policy scorer, a customer-safe split). It is imported, never run on its own.
- `07_engine.ipynb` is the test report: it prepares X5, Starbucks and Hillstrom into the standard shape, feeds each one to the same engine, and prints the results and the K7 verdict. This is the file that is run (Run All); it loads the engine automatically.
- Why split: the same engine file will power the web app (Step 11) and any Indian company's pilot data, with no code copied.

**What a new company must provide:** its customer table plus **one randomized test**, even a small pilot where some customers randomly get nothing. Without it, no model can separate "bought because of the offer" from "would have bought anyway".

**The safety margin:** the engine starts from the best option on average and switches to a customer's personal best only when it wins by a margin the engine learns from the data. If personalising does not reliably pay, it falls back to the best single option, so it is never worse than the best blanket policy.

&#91;embedded content: next-best-offer engine · how one customer gets one offer\]

#### How it works

| Stage | What we do | Why |
| --- | --- | --- |
| 1. Customer history | For each customer-wave, build measures from before the wave: past spend and visits, past offers received, viewed and completed, plus age, income, membership | The model must learn from the past only |
| 2. One model per option | For each offer type, learn the net value it adds over no offer (an uplift model per option, as in Step 4) | Gives four predicted values per customer |
| 3. Pick the best | Send the option with the highest predicted value; send nothing if none beats zero | The engine's decision |
| 4. Fair test | Split by customer: 80% build, 20% locked | No customer appears in both halves |
| 5. Policy value | On the locked 20%, customers whose random offer happens to match the engine's choice show what the engine would earn; each is weighted by the chance of that offer | Standard way to score a decision rule offline |
| 6. Same on Hillstrom | Men's email, women's email or none per customer, scored on real data | Real-data check |

#### Policies compared

| Policy | Rule |
| --- | --- |
| Send nothing | Baseline |
| Same offer to everyone | All reminders, all discounts, or all buy-one-get-one |
| Random offer | What the experiment did |
| Segment rules | Step 6's best offer per group (tenure, income) |
| **Next-best-offer engine** | The model's choice per customer |

#### K7 gate

| Check | Pass mark |
| --- | --- |
| Never worse than the best blanket policy | Engine minus best single option: 95% range includes or exceeds zero, on Starbucks and Hillstrom |
| Beats both blanket policies when contact costs money | On X5 with a message cost: engine beats message-everyone (range above zero) and message-nobody |
| Personalising the offer type | Reported honestly: kept only where the data shows it pays |

#### Results: K7 passed (run 23 Oct 2026, identical on Vipul's laptop and in the cloud)

**Headline: targeting whom to contact creates real value when contacts cost money; personalising which offer only pays when customers truly differ, and the engine detects when they do not.**

**X5, whom to contact.** Value = buy rate minus message cost. A cost of 0.033 means one message costs 3.3% of the profit on a purchase, the break-even point for messaging everyone.

| Cost of one message | Message everyone | Message nobody | **Engine** | Engine messages | Engine vs everyone (95% range) |
| --- | --- | --- | --- | --- | --- |
| 0 (free) | **0.634** | 0.604 | 0.631 | 90% | −0.003 (−0.006 to 0.000) |
| 0.02 | 0.614 | 0.604 | **0.620** | 57% | +0.006 (+0.000 to +0.012) |
| 0.033 | 0.601 | 0.604 | **0.614** | 38% | +0.014 (+0.006 to +0.020) |
| 0.05 | 0.584 | 0.604 | **0.611** | 22% | +0.027 (+0.019 to +0.035) |

&#91;image: When messages cost money, the engine beats both blanket policies\]

The more a message costs, the fewer people the engine contacts, and the bigger its lead. When messages are free, messaging everyone is as good, which is the correct answer.

**Starbucks, which offer.** Value = spend in 72 hours minus reward paid, per customer.

| Policy | Value | 95% range |
| --- | --- | --- |
| Send nothing | 7.49 | 6.83 to 8.24 |
| Random offers (what the test did) | 10.53 | 10.10 to 11.00 |
| All reminders | 12.60 | 11.36 to 14.02 |
| Best single offer to all (spend 10, get 2, 10 days) | **16.10** | 14.24 to 18.44 |
| Personalise every customer, no margin | 14.50 | 12.85 to 16.34 |
| **Nudge engine** (95% best offer) | **16.11** | 14.31 to 18.34 |

The engine's win is choosing the best offer from the data: +53% over random offers and +115% over nothing. Personalising every customer loses 1.6 per customer (range −3.4 to −0.1): the differences between customers are smaller than the model's error. The learned margin spotted this and kept 95% of customers on the best offer.

**Hillstrom, which email.** Men's email to all earns 1.27 per customer against 0.63 for no email. Personalising (1.13) and a men's/women's rule (1.07) did not beat it, so the engine learned an infinite margin and sends the men's email to everyone.

| K7 check | Result | Verdict |
| --- | --- | --- |
| Never worse than best blanket policy (Starbucks) | −0.02 (−0.36 to +0.33) | Pass |
| Never worse than best blanket policy (Hillstrom) | 0.00, same policy | Pass |
| Beats message-everyone at cost 0.033 (X5) | +0.014 (+0.006 to +0.020) | Pass |
| Beats message-nobody at cost 0.033 (X5) | 0.614 vs 0.604 | Pass |

#### How we know the numbers are right

- **Reproduced exactly:** the laptop run matches the cloud run to the last digit.
- **Sanity checks:** "send nothing" equals the no-offer group's average, and every blanket policy minus nothing matches Step 6's average effects within the test-half noise.
- **No peeking:** the best offer and the margin were chosen on the 80% build half only; every score is on the locked 20%, split by customer.
- **Honest limit:** the Starbucks test half has about 1,500 rows per offer, so ranges are wide (about ±2 per customer); small personal gains could exist and stay invisible at this size.

**Interview question this prepares:** *"Does personalisation always beat a single best offer?"*

> No, and my engine measures it instead of assuming. On X5, when a message cost as much as its average gain, the engine contacted 38% of customers and beat both messaging everyone and messaging no one. On Starbucks, personalising every customer lost money, because the differences between customers were smaller than the model's error, so the engine learned to send the best single offer. Personalise only where the data proves it pays.

### Step 8 · Money simulator and budget optimiser in rupees (PASS)

**The question it answers:** "I have ₹5 lakh. Whom do I contact, with which offer, and what profit comes back?" Steps 1–7 speak in model units (extra buyers, value per customer). Step 8 translates them into rupees and a budget plan, the language a CEO decides in.

#### The one equation

**Profit per customer, per option = extra buyers × margin − offer cost × everyone who uses it − contact cost**

Every option fits this equation, but each pays out differently. That difference is the heart of the step.

| Option | When you pay | Who you pay | Cost rule |
| --- | --- | --- | --- |
| SMS / WhatsApp / email reminder | On sending | Everyone contacted | Contact cost only |
| Discount (e.g. ₹50 off) | On purchase | Every buyer, including those who would buy anyway | Discount × all buyers |
| Cashback (paid after buying) | After purchase, if redeemed | Buyers who redeem | Cashback × buyers × redemption rate |
| Wallet credit (given upfront) | When spent | Whoever spends it | Credit × usage rate |
| Freebie (free delivery, bundle) | On purchase | Every buyer | Freebie cost × buyers |

#### Worked example (margin ₹200 per purchase)

| Customer | Option | Buy chance | Extra profit | Offer cost | Net |
| --- | --- | --- | --- | --- | --- |
| Regular (60% buy anyway) | SMS reminder | 63% | +₹6 | ₹0.20 | +₹5.80 (best) |
| Regular | ₹50 discount | 66% | +₹12 | ₹33 | −₹21 |
| Regular | ₹40 cashback, 70% redeem | 67% | +₹14 | ₹18.80 | −₹5 |
| Lapsed (10% buy anyway) | SMS reminder | 13% | +₹6 | ₹0.20 | +₹5.80 |
| Lapsed | ₹50 discount | 30% | +₹40 | ₹15 | +₹25 (best) |

**The trap it catches:** a discount is paid to people who would have bought anyway. For a regular shopper, the discount loses money even though it shows the biggest lift; for a lapsed shopper it is the best choice. This is the Step 6 finding, now in rupees.

#### Where each option's uplift comes from (honest data limit)

- **X5 (retail, SMS only):** whom to message.
- **Starbucks (discount, buy-one-get-one, reminder, with known reward amounts):** which offer.
- **Hillstrom (emails only):** which message.
- Each option's uplift is taken only from a dataset where that option was actually tested at random. For a real Indian company, one pilot that tests all options feeds the engine and the simulator directly.

#### What will be built

1. **Rupee assumptions:** margin, SMS, WhatsApp and email cost, discount size, cashback size, redemption rate. Indian benchmarks are researched with sources; every one stays adjustable.
2. **Profit curve:** total profit as more customers are contacted, best first. It rises, peaks, then falls; the peak is the best number of customers to contact.
3. **Budget optimiser:** for a budget of ₹X, pick customers and options by best rupee return until the money runs out.
4. **Head-to-head:** against message everyone, message nobody, and target likely buyers (the usual industry approach).
5. **Stress test:** margin halved, SMS cost doubled, model 30% too optimistic. Does the plan still make money?
6. **Honesty check:** profit measured on the real outcomes of locked test customers, with 95% ranges, not on predictions alone.

#### K5 gate

- **Pass:** the optimised plan earns more than message everyone and likely buyers, its 95% range is above zero at realistic Indian costs, and it still wins under the stress tests.
- **Fail:** report honestly where and why it breaks.

**Files:** `08_money.ipynb` (run with Run All); the money functions are added to `nudge_engine.py` so the web app reuses them.

**Interview line:** "I converted uplift scores into a rupee budget plan, found the profit-maximising number of customers to contact, and showed that a blanket discount destroys margin while a targeted one creates it."

#### Results: K5 passed (run 24 Oct 2026, identical on Vipul's laptop and in the cloud)

**Headline:** with a ₹20,000 WhatsApp budget, the uplift model earns **₹2.44 lakh**; the usual likely-buyer model earns **₹3,300** with the same money. Whom you pay to contact decides the profit.

**How the numbers were measured (no guessing):**

- Every profit figure comes from the **40,008 locked test customers** the models never saw, split at random into messaged and not messaged.
- For any chosen group (say the top 20%): buy rate of its messaged half − buy rate of its not-messaged half = real lift; lift × group size = **real extra buyers**.
- Rupees = extra buyers × ₹150 profit per purchase (₹1,000 basket × 15% grocery margin) − contacts × channel cost. Scaled to 1 lakh customers.
- **95% ranges:** the test is re-run 200 times on reshuffled samples to see how far the answer could move by chance.

**A1 · Profit curve (SMS at ₹0.10).** The best plan messages **95%** of customers: 3,370 extra buyers, ₹4.96 lakh profit (range ₹3.3 to ₹6.2 lakh). SMS is so cheap that nearly everyone is worth one; only the bottom 5%, whom the message pushes away, are dropped. At small budgets the uplift ranking is far ahead of both the likely-buyer model and random.

&#91;image: Profit curve: uplift vs likely-buyer vs random\]

**A2 · Channel ladder: the costlier the channel, the more targeting matters.**

| Channel | Cost per contact | Break-even lift | Best share to contact | Saved by targeting (per lakh customers) |
| --- | --- | --- | --- | --- |
| Email | ₹0.01 | 0.01 pts | 95% | ₹6,900 |
| SMS | ₹0.10 | 0.07 pts | 95% | ₹7,400 |
| WhatsApp | ₹1.02 | 0.68 pts | 90% | ₹13,700 |
| AI voice call | ₹3.33 | 2.22 pts | 70% | ₹71,700 |

**A3 · Budget optimiser.** When money is limited, whom you pick decides everything. At ₹20k the uplift model beats the likely-buyer model by ₹2.46 lakh (95% range ₹1.8 to ₹3.2 lakh). The likely-buyer model picks people who would buy anyway, so the message adds almost nothing.

&#91;image: Budget optimiser: profit at each WhatsApp budget\]

**B1 · Offers: lift is not profit.** Per customer offered: the reminder nets ₹194 at zero reward cost; the discount brings more sales (₹264 extra profit) but its ₹63 reward eats almost all the gain (net ₹201); the free item (BOGO) wins (net ₹258) because it costs only what the item costs to make (25% of its price at a 75% café margin), while a discount costs its full face value.

&#91;image: What each offer earns, costs and leaves\]

**B2 · Personalising the offer.** The engine chose the free item for everyone: as in Step 7, personalising did not reliably pay here, and the engine did not force it.

**B3 · Limited offer budget.** If offers go to only 40% of customers, engine ranking earns ₹627 vs ₹497 per customer for a random 40% (+₹133, range ₹83 to ₹189). With offers for everyone, ranking stops mattering, as expected.

&#91;image: Offer budget: engine-ranked vs random\]

**B4 · Untested options: extra buying needed to break even** (percentage points; the real X5 SMS gave 3.3).

| Option | Regular (60% buy anyway) | Occasional (30%) | Lapsed (10%) |
| --- | --- | --- | --- |
| SMS reminder | 0.1 | 0.1 | 0.1 |
| WhatsApp reminder | 0.7 | 0.7 | 0.7 |
| ₹30 wallet credit, 75% used | 10.7 | 5.4 | 1.8 |
| ₹50 cashback, 75% redeemed | 20.1 | 10.1 | 3.4 |
| ₹50 instant discount | 30.1 | 15.1 | 5.1 |
| Free grocery item worth ₹100 (costs ₹85) | 78.6 | 39.4 | 13.2 |

A discount to a regular customer would need 30 points of extra buying: it never pays. For lapsed customers a wallet credit needs only 1.8 points, so it is **the first pilot worth running**. A free grocery item is expensive because grocery margin is thin; freebies suit high-margin businesses.

**C · Stress test.** With the margin halved, WhatsApp cost doubled, or the model 30% too optimistic, the plan stays profitable and beats contacting everyone. With all three at once, the old plan loses ₹13,800 per lakh customers (contacting everyone loses ₹29,500); **re-running the optimiser** cuts contacts to 16% and still makes ₹55,000. When costs change, re-plan: that is why an optimiser beats a fixed rule.

&#91;image: Stress test: old plan, re-optimised plan, contact everyone\]

| K5 check | Result |
| --- | --- |
| Budget-limited: uplift beats likely-buyer, 95% range above zero (₹20k WhatsApp) | Pass: +₹2.46 lakh (₹1.8 to ₹3.2 lakh) |
| Offer budget (40%): engine ranking beats random, 95% range above zero | Pass: +₹133 (₹83 to ₹189) |
| Stress: re-optimised plan profitable in every scenario | Pass: lowest ₹55,000 |
| Stress: old plan never loses to contacting everyone | Pass: 5 of 5 |
| Chosen SMS plan profit, 95% range above zero | Pass: ₹3.3 to ₹6.2 lakh |

#### What Step 8 proves

- The project now speaks rupees: whom to contact, through which channel, with which offer, for what budget.
- It knows **when targeting matters**: expensive channels, limited budgets and costly offers. With a cheap channel and no budget limit, it correctly says "contact almost everyone".
- It tells a manager **which new offer is worth piloting** before spending on it.

**Interview question:** "If messaging is so cheap, why target at all?" **Answer:** "For SMS, you mostly shouldn't: my optimiser messages 95%. Targeting pays when each contact or offer costs real money or the budget is capped. With ₹20,000 of WhatsApp budget, my model makes ₹2.4 lakh against ₹3,300 for the usual likely-buyer approach, and a ₹50 discount to a regular shopper would need a 30-point jump in buying just to break even."

### Step 9 · Measurement playbook: keep proving it works (PASS)

**The question it answers:** "Once a company runs Nudge every month, how does it keep proving the profit is real, and know when the model has gone stale?" Steps 1–8 used one clean random test. In real life, once you start targeting, the clean test disappears unless you protect it on purpose.

#### The six parts

| Part | Question | Method |
| --- | --- | --- |
| A | Why must a control group exist? | Compare a naive campaign report with the fair one on the same customers |
| B | How big should the permanent control group be? | Sample-size formula (lift to detect, base buy rate, 95% confidence, 80% power), checked by simulation on real X5 customers; its cost in rupees |
| C | How do we keep learning? | Retrain the model on targeted-only data vs data with a random exploration slice, and score each on the locked exam |
| D | When is the model stale? | Drift check (PSI) on every customer measure, plus a lift-ladder check, each with traffic-light thresholds |
| E | What is the best time to send? | Design of a randomised send-time test, with the customers it needs |
| F | The playbook | One page: what to hold back, what to track, when to retrain |

#### K8 gate (defined for this step)

- The sample-size formula must match the simulation (power within 77–83% when the formula says 80%).
- The naive report must be shown to overstate the true effect.
- Retraining on targeted-only data must be shown to fail, and enough random exploration must recover most of the clean model's quality.
- The drift monitor must flag a simulated shift and stay quiet when nothing changed.

**Files:** `09_measure.ipynb` (Run All); measurement functions added to `nudge_engine.py`.

#### Results: K8 passed (run 24 Oct 2026, identical on Vipul's laptop and in the cloud)

**Headline:** without a control group, a normal campaign report credits the message with **8.6× the buyers it really caused**, and can make a **loss-making campaign look like ₹105 profit per call**. Once a company starts targeting, it also destroys the data it needs to retrain, unless it keeps a little randomness and records it.

| Part | Finding | Number |
| --- | --- | --- |
| A · Naive vs fair report | Most buyers would have bought anyway | 15,650 claimed vs 1,820 caused (8.6×) |
| A2 · Decision flip | AI calls to the bottom half look profitable, but are not | ₹105 vs −₹0.47 per call |
| B · Control-group size | Formula verified on real customers | 80% promised, 79% measured |
| C · Retraining on targeted data | Model becomes worse than random | −71% of clean quality |
| C2 · Cost of that stale model | Profit lost in the top 30% | about ₹1.78 lakh per campaign |
| C3 · Record the chance | Weighting rescues normal campaign data | 31% → 61% of clean quality |
| D · Real drift, 4 months | Behaviour stable, New Year included | largest PSI 0.043 (green) |
| D2 · Lift ladder | Model healthy, ladder in order | 0.95 / 2.88 / 5.65 pts |

**A · Why a control group is non-negotiable.** The top 30% by uplift were messaged. 52.2% of them bought, but 46.1% of look-alikes who were held back also bought. The message caused only the 6.1-point gap: 12% of the buyers. A report without a control group claims all of them.

&#91;image: Naive vs fair report\]

**A2 · The decision flip.** With AI voice calls (₹3.33 each) to the bottom half of customers, the naive report shows ₹105 profit per call; the fair report shows −₹0.47 (95% range −₹2.36 to +₹1.41), at best break-even. A company trusting the usual report would scale up a campaign that does not pay. The top half, by contrast, really earns ₹3.21 per call (range ₹1.13 to ₹5.28).

**B · How big the permanent control group should be.** The goal is to catch it if the lift ever halves (from 3.3 to about 1.7 points).

- The formula says 3,346 customers per group detect the real 3.3-point lift 80% of the time. Drawing groups of that size from real X5 customers 2,000 times detected it **79%** of the time: the formula can be trusted.
- Customers per group needed: 1 point → 37,400 · 2 points → 9,300 · 5 points → 1,500.

| Customers per campaign | Smallest control share that catches a halving | Lost sales from holding back |
| --- | --- | --- |
| 1 lakh | 10% (10,000 customers) | ₹48,800 per campaign |
| 10 lakh | 1–2% | ₹48,800 to ₹97,700 per campaign |

Bigger companies need a smaller share, because 1% of a large base is already plenty of people. A 2-point test needs 18,600 customers in total: 4 weeks at 5,000 contacts a week, 1 week at 50,000.

&#91;image: Control share vs minimum detectable lift\]

**C · The trap of targeting.** The same simple uplift model was retrained on different kinds of data and scored on the locked exam.

| Training data | Customers | Top-30% lift | Quality vs clean test |
| --- | --- | --- | --- |
| Clean random test | 160,031 | 5.5 pts | 100% |
| Targeted only (top 30% messaged, rest not) | 79,872 | 1.6 pts | −71% |
| Random slice, 8k–16k | 8,001–16,003 | 5.0–5.2 pts | 47–55% |
| Random slice, 32k | 32,006 | 5.5 pts | 63% |
| Random slice, 48k–80k | 48,009–80,015 | 5.4–5.5 pts | 75–76% |

After targeting, every high scorer got the message and no low scorer did, so there is no fair comparison left and the model learns nonsense: its top 30% shows 1.6 points of lift, below the 3.3 average. **Cost (C2):** that lost lift is worth about **₹1.78 lakh per campaign** of 1 lakh customers.

&#91;image: Exploration slice size vs model quality\]

**C3 · The industry fix: explore inside every decision, and record the chance.** The targeting rule keeps 20% randomness (a top-30% customer is messaged with a 90% chance, everyone else with a 10% chance) and records each customer's chance. When retraining, each customer is weighted by 1 ÷ that chance, so rare cases (a low scorer who was messaged) count more and the targeting bias is undone. This is **inverse propensity weighting**, the standard way large companies learn from their own targeted campaigns.

| Retraining on normal targeted-campaign data (4 replays) | Top-30% lift | Quality vs clean test |
| --- | --- | --- |
| Ignore the recorded chance | 4.0 pts | 31% |
| **Use the recorded chance** | **5.3 pts** | **61%** |

**D · When is the model stale?**

- **Alarm calibration:** quiet when nothing changed (largest PSI 0.000); fires on a festive-style shift of bills and spend +40% with more frequent visits (largest PSI 0.846).
- **Real drift across 4 months** (400,162 customers, four 4-week windows from 27 Nov 2018 to 18 Mar 2019, each compared with the build period): every measure stays green, largest PSI 0.043, New Year included. Average 4-week spend moved only from 2,274 to 2,484 roubles. **Meaning:** the model's inputs were stable, so no seasonal retrain was needed in this period. The alarm stays in the playbook because an Indian festive season (Diwali, sale weeks) can shift behaviour far more.

&#91;image: Real month-by-month drift vs build period\]

- **Lift-ladder alarm:** real lift is 0.95 points in the bottom third, 2.88 in the middle and 5.65 in the top third, so the model is healthy. Rule: if the top third falls below 5.0 points (1.5× the average) or the order breaks, investigate and retrain.

&#91;image: Lift ladder by model third\]

**E · Best time to send: pilot design.** X5 never varied send time, so it cannot be measured from this data. The design: four random groups (control, 9 am, 7 pm, on the day the customer is due). Detecting a 2-point difference between send times needs about 9,000 per group (36,000 in total); a 1-point difference needs about 36,000 per group, worth it only for large bases.

#### The one-page playbook

| What | Rule | Why |
| --- | --- | --- |
| Permanent control group | Hold back a random 10% (bases near 1 lakh) or 1–2% (near 10 lakh), every campaign | Proves the profit; catches a halving of lift |
| Explore and record | Targeting keeps about 20% randomness and records each customer's chance (or a random slice of 30,000+) | Clean data to retrain; targeted-only data makes the model worse than random |
| Report | Always contacted vs control: extra buyers, extra profit, 95% range | Naive reports overstate about 9× and can make a losing campaign look profitable |
| Drift alarm | Monthly PSI on every customer measure vs the build period | Amber 0.1–0.25 watch; red above 0.25 retrain; watch festive seasons |
| Lift-ladder alarm | Each campaign: real lift in top, middle and bottom thirds | Top third below 1.5× average or out of order: retrain |
| Retrain | Quarterly on exploration data, weighted by recorded chance, or at once on a red alarm | Re-run the Step 4 model check before switching |
| Send-time test | Once: control, morning, evening, when due; about 9,000–17,000 per group | Adds the best time to send |

| K8 check | Result |
| --- | --- |
| Naive report overstates the true effect (at least 3×) | Pass: 8.6× |
| Decision flip: naive shows profit, fair shows break-even or loss | Pass: ₹105 vs −₹0.47 per call |
| Sample-size formula matches simulation (77–83%) | Pass: 79.0% |
| Targeted-only retraining fails (under half the clean Qini) | Pass: −71% |
| Enough random exploration recovers 60%+ of clean quality | Pass: 75–76% at 48k+ |
| Using the recorded chance beats ignoring it | Pass: 61% vs 31% |
| Drift alarm quiet when nothing changed | Pass: PSI 0.000 |
| Drift alarm fires on a deliberate shift | Pass: PSI 0.846 |

#### How this step was improved after its first version

The first version passed its checks but was weak in two places, so it was rebuilt before being accepted:

- Its drift check compared two random halves of the same customers, which cannot show drift by design, and its festive month was simulated. **Fix:** real month-by-month behaviour from the 679 MB purchase history, with the simulated shift kept only to calibrate the alarm.
- It spoke in statistics, not money. **Fix:** a decision flip in rupees, the rupee cost of a stale model, and the recorded-chance method that lets normal campaign data be reused.

#### What Step 9 proves

- Honest measurement: a naive report can overstate the effect almost 9× and turn a losing campaign into an apparent winner.
- Experiment design: the control group is sized by power analysis and the maths is verified on real data.
- Production thinking: targeting destroys its own training data, and the fix (explore and record the chance, then weight) recovers it.
- Monitoring: drift and lift-ladder alarms with clear thresholds, tested on real months.

**Interview question:** "Your model is live. How do you know it still works, and how do you retrain it?" **Answer:** "I keep a permanent control group sized by power analysis, 10% for a 1-lakh base, because without it a normal report overstates the effect 8.6× and can make a loss-making campaign look like ₹105 profit per call. Targeting also destroys training data: retraining on targeted-only data made my model worse than random, costing about ₹1.8 lakh per campaign. So targeting keeps 20% randomness and records each customer's chance, and I retrain with inverse propensity weights, which doubled the retrained model's quality. Drift and lift-ladder alarms tell me when to retrain."

### Step 10 · The contrast case: what goes wrong without a random test (PASS)

**The question it answers:** most companies never run a random test. They target the customers they like, then compare them with everyone else. What answer does that give, and can it be trusted?

**Data:** Dunnhumby *The Complete Journey*: 2,469 US grocery households, one year of baskets and 27 real campaigns where **the company chose whom to target**. Test case: Campaign 8 (8 May to 25 June 2017), sent to 825 households not in earlier campaigns.

#### Method

| Approach | What it compares | Why |
| --- | --- | --- |
| Naive | Targeted households vs everyone else, during the campaign | How most campaign results are reported |
| Careful attempt 1 | Targeted vs **never-targeted** look-alikes | The best possible without a random test |
| Careful attempt 2 | Targeted vs look-alikes the company **targeted later** | An equally defensible choice: the same kind of customer |

The careful method has three parts:

1. **Match:** each targeted household is paired with the most similar control household on weekly spend and trips before the campaign (weeks 2–13); the worst 10% of matches are dropped.
2. **Placebo check:** in weeks 14–19 there was no campaign yet, so matched pairs should spend the same. If they do not, the match is not trusted.
3. **Difference-in-differences:** the gap between pairs during the campaign minus their gap in the placebo weeks, with a 95% range from 1,000 bootstrap repeats.

#### Results: K9 passed (run 24 Oct 2026, identical on Vipul's laptop and in the cloud)

**Headline:** the naive report says the campaign group spent **5.6× more**. But they already spent **6.3× more before the campaign started**: the company picked its best customers. Two careful methods, both passing their placebo checks, then give **confident opposite answers**.

|  | Targeted, $ per week | Never targeted, $ per week | Ratio |
| --- | --- | --- | --- |
| Before the campaign (weeks 2–13) | 56.6 | 9.0 | 6.3× |
| During the campaign (weeks 20–26) | 55.0 | 9.9 | 5.6× |

&#91;image: Weekly spend: targeted vs targeted later vs never targeted\]

| Careful method, control group | Matched pairs | Placebo check | Effect on spend | 95% range |
| --- | --- | --- | --- | --- |
| Never-targeted look-alikes | 742 | Pass (gap −$2.68/week) | **+10.7%** | +5.1% to +16.6% |
| Targeted-later look-alikes | 742 | Pass (gap +$2.23/week) | **−6.5%** | −11.2% to −1.3% |

&#91;image: Same campaign, two careful methods, opposite answers\]

| Source | Estimate | Trust |
| --- | --- | --- |
| Complete Journey, naive report | 5.6× more spend | None: mostly selection |
| Complete Journey, careful vs never targeted | +10.7% | Confident, but depends on the choice |
| Complete Journey, careful vs targeted later | −6.5% | Confident, but depends on the choice |
| **X5 random test (Step 1)** | **+3.3 points buy rate** | **+2.9 to +3.8 points: one answer** |

**Why they disagree:** never-targeted households are light shoppers, so even matched ones may drift differently; targeted-later households are heavy shoppers the company liked, perhaps already slowing down. Each choice hides a different bias, and no test inside the data can say which is right. Only randomisation removes the choice.

| K9 check | Result |
| --- | --- |
| Naive report shows a big effect (over 3×) | Pass: 5.6× |
| The gap already existed before the campaign (selection bias) | Pass: 6.3× before |
| Both careful attempts pass their placebo checks | Pass |
| The two careful answers disagree in sign | Pass: +10.7% vs −6.5% |

#### What Step 10 proves

- Naive campaign reports mostly measure **who was chosen**, not what the campaign did.
- Even careful methods (matching, placebo checks, difference-in-differences) can give **confident opposite answers** on non-random data.
- This is why every step of Nudge is built on a randomised control group, and why Step 9 keeps one permanently.

**Interview question:** "Our campaign group spent 5.6× more. Isn't that proof it worked?" **Answer:** "No. On real data I showed that group already spent 6.3× more before the campaign, because the company picked its best customers. Then I ran two careful matched difference-in-differences analyses; both passed placebo checks, and they said +11% and −7%. Without a random control group, the answer depends on an untestable choice. With one, as in X5, you get a single answer: +3.3 points, range 2.9 to 3.8."

## 8. Build roadmap

The full build takes about four weeks; the go-or-stop check (K4) comes in week 1, before most of the effort.

| Step | Week | Work | Output | Gate | Status |
| --- | --- | --- | --- | --- | --- |
| 0 | 1 | Setup: Python tools, VS Code, data downloads | Working environment |  | Done |
| 1 | 1 | Data health check and fair test on X5 | Fairness and overall lift | K1, K2 | Done: data passed health check |
| 2 | 1 | Customer profiles from 45.8M purchase rows | One feature row per customer (67 measures) | K3 |  Done: K3 passed |
| 3 | 1 | Quick uplift model and first Qini chart | Go or stop decision | K4 |  Done: K4 GO |
| 4 | 2 | Model selection: 7 uplift methods, cross-validation, tuning, locked final exam | Champion model (+27% Qini), scores for all customers |  |  Done |
| 5 | 2 | Who to message: persuadable personas and a head-to-head with a normal likely-buyer model | Persona table, uplift vs likely-buyer comparison |  |  Done: uplift 12x likely-buyer |
| 6 | 2 | Load Hillstrom and Starbucks; balance checks; uplift per offer type | Offer-level uplift | K6 |  Done: K6 passed |
| 7 | 3 | Next-best-offer: best action per customer | Action per customer | K7 |  Done: K7 passed |
| 8 | 3 | Money simulator at reminder, offer and credit costs; budget optimiser | Policy comparison, budget split | K5 | Done: K5 passed |
| 9 | 3 | Measurement playbook: holdout size, test length, retrain plan | One-page playbook |  | Done: K8 passed |
| 10 | 3 | Contrast case: naive vs fair estimate (Complete Journey) | Why-experiments chapter | K9 | Done: K9 passed |
| 11 | 4 | Web app (Streamlit) | Working app |  |  |
| 12 | 4 | AI assistant inside the app | Plain-language answers |  |  |
| 13 | 4 | India memo, README, CV bullet, interview answers | Finished package |  |  |

## 9. Risks

The largest risk is K4: if the model cannot beat random targeting, the project stops early.

| Risk | Mitigation |
| --- | --- |
| Model does not beat random targeting | Tested at step 3, before most effort; stop if it fails |
| 45.8M rows strain a laptop | Read the file with DuckDB, which summarises without loading everything into memory |
| No cost or margin data | State assumptions openly; show results across a range of message costs |
| Not Indian data | India memo applying the same logic to quick-commerce coupons, push and SMS |
| Dataset is known in the uplift community | Differentiate through the decision rule, the app and the non-random contrast case |

## 10. Interview prep

The CV bullet gets its numbers after K4 and K5; the answers below get written as each step finishes.

> Built Nudge, a next-best-offer and budget engine trained on 3 randomized experiments (200K customers, 45.8M purchases); uplift targeting kept Y% of sales lift at Z% lower offer cost.

1. How do you know the message caused the purchases?
2. Why uplift modelling and not a normal "will they buy" model?
3. How did you test the model? What is a Qini curve?
4. Where do the cost numbers come from?
5. Why is non-random targeting dangerous?
6. How would a Zepto or Nykaa team use this tomorrow?
7. What would you do with more time or real company data?

Added with the wider scope:

8. How do you choose between a reminder, a discount and a credit for one customer?
9. How does the budget optimiser decide who gets what?
10. How big should the no-contact group be in the next campaign, and why keep one at all?
