#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function
import sys
import argparse
import decimal
import json

MONTHS_IN_YEAR = 12
DOLLAR_QUANTIZE = decimal.Decimal('.01')
INFLATION = decimal.Decimal('1.5')

def dollar(f, round=decimal.ROUND_CEILING):
    """
    This function rounds the passed float to 2 decimal places.
    """
    if not isinstance(f, decimal.Decimal):
        f = decimal.Decimal(str(f))
    return f.quantize(DOLLAR_QUANTIZE, rounding=round)

def inflate(amount, percent):
    return amount + (amount * (percent / 100))

class Rent:
    def __init__(self):
        self._rent = dollar(0.0)
        self._insurance = dollar(0.0)
        self._expense = dollar(0.0)
        self._hoa = dollar(0.0)
        self._rent_increase_percent = decimal.Decimal(0.0)
        self._idle_months = decimal.Decimal(0.0)
        self._next_rent = dollar(0.0)
        self._next_insurance = dollar(0.0)
        self._next_expense = dollar(0.0)
        self._next_hoa = dollar(0.0)

    def setup(self, params):
        if (params._rent != 0 and params._rent_per_sqft != 0):
            raise ValueError("Cannot have both rent and rent-per-sq-feet")
        if ((params._rent_per_sqft == 0 and params._sqft !=0) or (params._sqft != 0 and params._rent_per_sqft == 0)):
            raise ValueError("sqft and rent-per-sq-feet must be both 0 or set to some value")
        if params._rent != 0.0 : 
            self._rent = dollar(params._rent)
        else:
            self._rent = dollar(params._sqft * params._rent_per_sqft)
        self._next_rent = self._rent
        self._insurance = dollar(params._insurance)
        self._next_insurance = self._insurance
        self._expense = dollar(params._expense)
        self._next_expense= self._expense
        self._hoa = dollar(params._hoa)
        self._next_hoa = self._hoa
        self._rent_increase_percent = decimal.Decimal(params._rent_increase_percent)
        self._idle_months = decimal.Decimal(params._idle_months)

    def rent(self):
        return self._rent

    def insurance(self):
        return self._insurance

    def expense(self):
        return self._expense

    def hoa(self):
        return self._hoa;

    def rent_increase_percent(self):
        return self._rent_increase_percent

    def idle_months(self):
        return self._idle_months

    def update_next(self):
        self._next_rent = inflate(self._next_rent, self._rent_increase_percent)
        self._next_insurance = inflate(self._next_insurance, INFLATION)
        self._next_expense = inflate(self._next_expense, INFLATION)
        self._next_hoa = inflate(self._next_hoa, INFLATION)

    def next_rent(self):
        return self._next_rent

    def next_insurance(self):
        return self._next_insurance

    def next_expense(self):
        return self._next_expense

    def next_hoa(self):
        return self._next_hoa

    def annual_rent(self):
        return self.next_rent() * (decimal.Decimal(MONTHS_IN_YEAR) - self._idle_months)

class Mortgage:
    def __init__(self):
        self._interest = decimal.Decimal(0.0)
        self._months = 0
        self._loan = dollar(0.0)
        self._value = dollar(0.0)
        self._down = dollar(0.0)
        self._taxrate = decimal.Decimal(0.0)
        self._tax_increase_percent = decimal.Decimal(0)
        self._appreciation_percent = decimal.Decimal(0)
        self._tax = decimal.Decimal(0.0)
        self._next_tax = decimal.Decimal(0.0)
        self._next_down = self._down
        self._next_real_down = self._down
        self._next_value = self._value
        self._equity = decimal.Decimal(0.0)

    def setup(self, params):
        self._interest = decimal.Decimal(decimal.Decimal(params._interest) / decimal.Decimal(100.0))
        self._months = decimal.Decimal(params._months)
        self._value = dollar(params._value)
        if (params._down != 0):
            self._down = dollar(params._down)
        else:
            self._down = dollar(self._value * decimal.Decimal(params._down_fraction))
        self._loan = dollar(self._value - self._down)
        self._equity = self._down
        self._taxrate = decimal.Decimal(params._taxrate)
        self._tax_increase_percent = decimal.Decimal(params._tax_increase_percent)
        self._appreciation_percent = decimal.Decimal(params._appreciation_percent)
        if (self._tax_increase_percent > self._appreciation_percent):
            self._tax_increase_percent = self._appreciation_percent
        self._tax = self._value * (self._taxrate / decimal.Decimal(100.0))
        self._next_tax = self._tax
        self._next_down = self._down
        self._next_real_down = self._down
        self._next_value = self._value

    def rate(self):
        return self._interest

    def month_growth(self):
        return decimal.Decimal(1.) + self._interest / decimal.Decimal(MONTHS_IN_YEAR)

    def apy(self):
        return self.month_growth() ** MONTHS_IN_YEAR - 1

    def loan_years(self):
        return float(self._months) / MONTHS_IN_YEAR

    def loan_months(self):
        return self._months

    def loan(self):
        return self._loan

    def value(self):
        return self._value

    def update_next(self, balance, principle):
        self._next_down = self._next_down + principle;
        self._next_real_down = inflate(self._next_real_down, INFLATION) + principle
        self._next_value = inflate(self._next_value, self._appreciation_percent)
        self._next_tax = inflate(self._next_tax, self._tax_increase_percent)
        self._equity = self._next_value - balance

    def next_value(self):
        return self._next_value

    def down(self):
        return self._down

    def next_down(self):
        return self._next_down

    def next_real_down(self):
        return self._next_real_down

    def equity(self):
        return self._equity

    def taxrate(self):
        return self._taxrate

    def tax_increase_percent(self):
        return self._tax_increase_percent

    def appreciation_percent(self):
        return self._appreciation_percent

    def next_tax(self):
        return self._next_tax

    def monthly_payment(self):
        pre_amt = decimal.Decimal(self.loan()) * decimal.Decimal(self.rate()) / (decimal.Decimal(MONTHS_IN_YEAR) * decimal.Decimal((decimal.Decimal(1.)-(decimal.Decimal(1.)/self.month_growth()) ** self.loan_months())))
        return dollar(pre_amt, round=decimal.ROUND_CEILING)

    def total_value(self, m_payment):
        return m_payment / self.rate() * (float(MONTHS_IN_YEAR) * (1.-(1./self.month_growth()) ** self.loan_months()))

    def annual_payment(self):
        return self.monthly_payment() * MONTHS_IN_YEAR

    def total_payout(self):
        return self.monthly_payment() * self.loan_months()

    def monthly_payment_schedule(self):
        monthly = self.monthly_payment()
        balance = dollar(self.loan())
        rate = decimal.Decimal(str(self.rate())).quantize(decimal.Decimal('.000001'))
        while True:
            interest_unrounded = balance * rate * decimal.Decimal(1)/MONTHS_IN_YEAR
            interest = dollar(interest_unrounded, round=decimal.ROUND_HALF_UP)
            if monthly >= balance + interest:
                principle = balance
                balance = decimal.Decimal(0.0)
                yield balance, principle, interest
                break
            principle = monthly - interest
            balance -= principle
            yield balance, principle, interest

class Config:
    
    def __init__(self):
        self._interest = 0.0
        self._months = 0.0
        self._value = 0.0
        self._down = 0.0
        self._down_fraction = 0.0
        self._rent = 0.0
        self._rent_per_sqft = 0.0
        self._insurance = 0.0
        self._taxrate = 0.0
        self._hoa = 0.0
        self._expense = 0.0
        self._rent_increaase_percent = 0.0
        self._tax_increase_percent = 0.0
        self._idle_months = 0.0
        self._sqft = 0.0
        self._appreciation_percent = 0.0

    def check(self):
        if self._interest <= 0.0:
            raise ValueError("Invalid Interest")
        if self._months <= 0.0:
            raise ValueError("Invalid Months")
        if self._down <= 0.0 and self._down_fraction <= 0.0:
            raise ValueError("Invalid down or down-fraction")
        if self._rent <= 0 and self._rent_per_sqft <= 0:
            raise ValueError("Invalid rent or rent-per-sq-feet")

    @staticmethod
    def save(previous, config) :
        if previous== None : 
            previous = Config()
        current = Config()

        if 'interest' in config:
            current._interest = config['interest']
        else:
            current._interest = previous._interest

        if 'months' in config:
            current._months = config['months']
        else:
            current._months = previous._months

        if 'insurance' in config:
            current._insurance = config['insurance']
        else:
            current._insurance = previous._insurance

        if 'down-fraction' in config and 'down' in config:
            raise ValueError('Both down-fraction and down not allowed')
        else:
            if 'down-fraction' not in config and 'down' not in config:
                current._down_fraction = previous._down_fraction
                current._down = previous._down
            else:
                if 'down-fraction' in config:
                    current._down_fraction = config['down-fraction']
                elif 'down' in config:
                    current._down = config['down']

        if 'rent-per-sq-feet' in config and 'rent' in config:
            raise ValueError('Both rent-per-sq-feet and rent are not allowed')
        else:
            if 'rent-per-sq-feet' not in config and 'rent' not in config:
                current._rent_per_sqft = previous._rent_per_sqft
                current._rent = previous._rent
            else:
                if 'rent-per-sq-feet' in config:
                    current._rent_per_sqft = config['rent-per-sq-feet']
                elif 'rent' in config:
                    current._rent = config['rent']

        if 'value' in config:
            current._value = config['value']
        else:
            current._value = previous._value

        if 'taxrate' in config:
            current._taxrate = config['taxrate']
        else:
            current._taxrate = previous._taxrate

        if 'hoa' in config:
            current._hoa = config['hoa']
        else:
            current._hoa = previous._hoa

        if 'expense' in config:
            current._expense = config['expense']
        else:
            current._expense = previous._expense

        if 'rent-increase-percent' in config:
            current._rent_increase_percent = config['rent-increase-percent']
        else:
            current._rent_increase_percent = previous._rent_increase_percent

        if 'tax-increase-percent' in config:
            current._tax_increase_percent = config['tax-increase-percent']
        else:
            current._tax_increase_percent = previous._tax_increase_percent

        if 'idle-months' in config:
            current._idle_months = config['idle-months']
        else:
            current._idle_months = previous._idle_months

        if 'appreciation-percent' in config:
            current._appreciation_percent = config['appreciation-percent']
        else:
            current._appreciation_percent = previous._appreciation_percent

        if 'sqft' in config:
            current._sqft = config['sqft']
        else:
            current._sqft = previous._sqft

        return current

def print_parameters(m, r):
    print('{0:>12s} {1:>12s} {2:>12s} {3:>12s} {4:>12s} {5:>12s} {6:>12s}'.format('Interest', 'months', 'loan', 'value', 'down', 'tax', 'tax inc %/y'))
    print('{0:>12.3f} {1:>12.0f} {2:>12.2f} {3:>12.2f} {4:>12.2f} {5:>12.2f}% {6:>12.0f}'.\
            format(m.rate() * decimal.Decimal(100), m.loan_months(), m.loan(), m.value(), m.down(), m.taxrate(), m.tax_increase_percent()))
    print('{0:>12s} {1:>12s} {2:>12s} {3:>12s} {4:>12s} {5:>12s} {6:>12s}'.format('value inc %/y', 'rent/m', 'insurance/m', 'expense/m', 'hoa/m', 'rent inc %/y', 'idle months/y'))
    print('{0:>12.0f} {1:>12.2f} {2:>12.2f} {3:>12.2f} {4:>12.2f} {5:>12.0f} {6:>12.2f}'.\
            format(m.appreciation_percent(), r.rent(), r.insurance(), r.expense(), r.hoa(), r.rent_increase_percent(), r.idle_months()))

def print_summary(m):
    print('{0:>25s}:  {1:>12.6f}'.format('Rate', m.rate()))
    print('{0:>25s}:  {1:>12.6f}'.format('Month Growth', m.month_growth()))
    print('{0:>25s}:  {1:>12.6f}'.format('APY', m.apy()))
    print('{0:>25s}:  {1:>12.0f}'.format('Payoff Years', m.loan_years()))
    print('{0:>25s}:  {1:>12.0f}'.format('Payoff Months', m.loan_months()))
    print('{0:>25s}:  {1:>12.2f}'.format('Amount', m.loan()))
    print('{0:>25s}:  {1:>12.2f}'.format('Monthly Payment', m.monthly_payment()))
    print('{0:>25s}:  {1:>12.2f}'.format('Annual Payment', m.annual_payment()))
    print('{0:>25s}:  {1:>12.2f}'.format('Total Payout', m.total_payout()))

def print_detail(m, r):
    yinterest = decimal.Decimal(0.0)
    yprinciple = decimal.Decimal(0.0)
    lequity = decimal.Decimal(m.down())
    cmonth = 0
    cyear = 1
    first = False

    print('{0:>40s}:'.format('Yearly Schedule'))
    print('{0:>12s} {1:>12s} {2:>12s} {3:>12s} {4:>12s} {5:>12s} {6:>12s} {7:>12s} {8:>12s} {9:>12s} {10:>12s}'.format('Year', 'Interest', 'Principle', 'Expense', 'Rent', 'Profit', 'Porf Pct', 'Cash Flow', 'ProfitWEq', 'PWEq Pct', 'PWREq Pct'))
    for balance, principle, interest in m.monthly_payment_schedule():
        yinterest = yinterest + interest
        yprinciple = yprinciple + principle
        cmonth = (cmonth + 1) % MONTHS_IN_YEAR

        if cmonth == 0:
            if first :
                first = False
                continue

            expense = (m.next_tax() + (r.next_expense() * MONTHS_IN_YEAR) + 
                      (r.next_hoa() * MONTHS_IN_YEAR) 
                      + (r.next_insurance() * MONTHS_IN_YEAR) + yinterest)
            rent = r.annual_rent() 
            profit = rent - expense
            profit_percent = (profit / m.next_down()) * 100
            cash_flow = rent - expense - yprinciple
            yequity = m.equity()
            profit_with_equity = profit + (yequity - lequity)
            profit_with_equity_percent = (profit_with_equity / m.next_down()) * 100
            profit_with_real_equity_percent = (profit_with_equity / m.next_real_down()) * 100
            print('{0:>12d} {1:>12.2f}  {2:>12.2f} {3:>12.2f} {4:>12.2f} {5:>12.2f} {6:>12.2f} {7:>12.2f} {8:>12.2f} {9:>12.2f} {10:>12.2f}'.format(cyear, yinterest, yprinciple, expense, rent, profit, profit_percent, cash_flow, profit_with_equity, profit_with_equity_percent, profit_with_real_equity_percent));
            yinterest = 0
            yprinciple = 0
            cyear = cyear + 1
            lequity = yequity
            m.update_next(balance, yprinciple)
            r.update_next()

    expense = (m.next_tax() + (r.next_expense() * MONTHS_IN_YEAR) + 
            (r.next_hoa() * MONTHS_IN_YEAR) 
            + (r.next_insurance() * MONTHS_IN_YEAR))
    rent = r.annual_rent()
    profit = rent - expense
    profit_percent = (profit / m.next_down()) * 100
    cash_flow = rent - expense - yprinciple
    yequity = m.equity()
    profit_with_equity = profit + (yequity - lequity)
    profit_with_equity_percent = (profit_with_equity / m.next_down()) * 100
    profit_with_real_equity_percent = (profit_with_equity / m.next_real_down()) * 100
    print('{0:>12d} {1:>12.2f}  {2:>12.2f} {3:>12.2f} {4:>12.2f} {5:>12.2f} {6:>12.2f} {7:>12.2f} {8:>12.2f} {9:>12.2f} {10:>12.2f}'.format(cyear, 0, 0, expense, rent, profit, profit_percent, cash_flow, profit_with_equity, profit_with_equity_percent,profit_with_real_equity_percent));

def main():
    parser = argparse.ArgumentParser(description='Mortgage Amortization Tools')
    parser.add_argument('-s', '--summary', default=False, dest='summary')
    parser.add_argument('-f', '--cfile', dest='cfile')
    parser.add_argument('-a', '--afile', default='./area.json', dest='afile')
    parser.add_argument('-g', '--gfile', default='./global.json', dest='gfile')
    args = parser.parse_args()

    params = None
    if args.gfile:
        try:
            with open(args.gfile) as global_config:
                config = json.load(global_config)
                params = Config.save(None, config)
        except FileNotFoundError:
            pass

    if args.afile:
        try:
            with open(args.afile) as area_config:
                config = json.load(area_config)
                params = Config.save(params, config)
        except FileNotFoundError:
            pass
        
    if args.cfile:
        try:
            with open(args.cfile) as config_file:
                config = json.load(config_file)
                params = Config.save(params, config)
        except FileNotFoundError:
            pass
        
    params.check()

    r = Rent()
    m = Mortgage()
    r.setup(params)
    m.setup(params)

    print_parameters(m,r)
    if args.summary:
        print_summary(m)
    else:
        print_detail(m, r)

if __name__ == '__main__':
    main()
