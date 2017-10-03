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
    def __init__(self, rent, insurance, expense, hoa, rent_increase_percent, idle_months):
        self._rent = dollar(rent)
        self._insurance = dollar(insurance)
        self._expense = dollar(expense)
        self._hoa = dollar(hoa)
        self._rent_increase_percent = decimal.Decimal(rent_increase_percent)
        self._idle_months = idle_months
        self._next_rent = dollar(0.0)
        self._next_insurance = dollar(0.0)
        self._next_expense = dollar(0.0)
        self._next_hoa = dollar(0.0)

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
        return self.idle_months

    def next_rent(self):
        if (self._next_rent == 0.0):
            self._next_rent = self.rent()
        else:
            self._next_rent = inflate(self._next_rent, self._rent_increase_percent)
        return self._next_rent

    def next_insurance(self):
        if (self._next_insurance == 0.0):
            self._next_insurance = self._insurance
        else:
            self._next_insurance = inflate(self._next_insurance, INFLATION)
        return self._next_insurance

    def next_expense(self):
        if (self._next_expense== 0.0):
            self._next_expense= self._expense
        else:
            self._next_expense = inflate(self._next_expense, INFLATION)
        return self._next_expense

    def next_hoa(self):
        if (self._next_hoa == 0.0):
            self._next_hoa = self._hoa
        else:
            self._next_hoa = inflate(self._next_hoa, INFLATION)
        return self._next_hoa

    def annual_rent(self):
        return self.next_rent() * (MONTHS_IN_YEAR - self._idle_months)

class Mortgage:
    def __init__(self, interest, months, amount, value, down, taxrate, tax_increase_percent):
        self._interest = float(interest)
        self._months = int(months)
        self._amount = dollar(amount)
        self._value = dollar(value)
        self._down = dollar(down)
        self._taxrate = dollar(taxrate)
        self._tax_increase_percent = decimal.Decimal(tax_increase_percent)
        self._tax = self._value * (self._taxrate / 100)
        self._next_tax = 0.0

    def rate(self):
        return self._interest

    def month_growth(self):
        return 1. + self._interest / MONTHS_IN_YEAR

    def apy(self):
        return self.month_growth() ** MONTHS_IN_YEAR - 1

    def loan_years(self):
        return float(self._months) / MONTHS_IN_YEAR

    def loan_months(self):
        return self._months

    def amount(self):
        return self._amount

    def value(self):
        return self._value

    def down(self):
        return self._down

    def taxrate(self):
        return self._taxrate

    def tax_increase_percent(self):
        return self._tax_increase_percent

    def next_tax(self):
        if (self._next_tax == 0.0):
            self._next_tax = self._tax
        else:
            self._next_tax = inflate(self._next_tax, self._tax_increase_percent)
        return self._next_tax


    def monthly_payment(self):
        pre_amt = float(self.amount()) * self.rate() / (float(MONTHS_IN_YEAR) * (1.-(1./self.month_growth()) ** self.loan_months()))
        return dollar(pre_amt, round=decimal.ROUND_CEILING)

    def total_value(self, m_payment):
        return m_payment / self.rate() * (float(MONTHS_IN_YEAR) * (1.-(1./self.month_growth()) ** self.loan_months()))

    def annual_payment(self):
        return self.monthly_payment() * MONTHS_IN_YEAR

    def total_payout(self):
        return self.monthly_payment() * self.loan_months()

    def monthly_payment_schedule(self):
        monthly = self.monthly_payment()
        balance = dollar(self.amount())
        rate = decimal.Decimal(str(self.rate())).quantize(decimal.Decimal('.000001'))
        while True:
            interest_unrounded = balance * rate * decimal.Decimal(1)/MONTHS_IN_YEAR
            interest = dollar(interest_unrounded, round=decimal.ROUND_HALF_UP)
            if monthly >= balance + interest:
                yield balance, interest
                break
            principle = monthly - interest
            yield principle, interest
            balance -= principle

def print_summary(m):
    print('{0:>25s}:  {1:>12.6f}'.format('Rate', m.rate()))
    print('{0:>25s}:  {1:>12.6f}'.format('Month Growth', m.month_growth()))
    print('{0:>25s}:  {1:>12.6f}'.format('APY', m.apy()))
    print('{0:>25s}:  {1:>12.0f}'.format('Payoff Years', m.loan_years()))
    print('{0:>25s}:  {1:>12.0f}'.format('Payoff Months', m.loan_months()))
    print('{0:>25s}:  {1:>12.2f}'.format('Amount', m.amount()))
    print('{0:>25s}:  {1:>12.2f}'.format('Monthly Payment', m.monthly_payment()))
    print('{0:>25s}:  {1:>12.2f}'.format('Annual Payment', m.annual_payment()))
    print('{0:>25s}:  {1:>12.2f}'.format('Total Payout', m.total_payout()))

def print_detail(m, r):
    yinterest = 0
    yprinciple = 0
    cmonth = 0

    print('{0:>25s}:'.format('Yearly Schedule'))
    print('{0:>12s} {1:>12s} {2:>12s} {3:>12s} {4:>12s} {5:>12s} {6:>12s}'.format('Interest', 'Principle', 'Expense', 'Rent', 'Profit', 'Porf Pct', 'Cash Flow'))
    for principle, interest in m.monthly_payment_schedule():
        yinterest = yinterest + interest
        yprinciple = yprinciple + principle
        cmonth = (cmonth + 1) % MONTHS_IN_YEAR

        if cmonth == 0:
            expense = (m.next_tax() + (r.next_expense() * MONTHS_IN_YEAR) + 
                      (r.next_hoa() * MONTHS_IN_YEAR) 
                      + (r.next_insurance() * MONTHS_IN_YEAR) + yinterest)
            rent = r.annual_rent() 
            profit = rent - expense
            profit_percent = (profit / m.down()) * 100
            cash_flow = rent - expense - yprinciple
            print('{0:>12.2f}  {1:>12.2f} {2:>12.2f} {3:>12.2f} {4:>12.2f} {5:>12.2f} {6:>12.2f}'.format(yinterest, yprinciple, expense, rent, profit, profit_percent, cash_flow));
            yinterest = 0
            yprinciple = 0

def main():
    parser = argparse.ArgumentParser(description='Mortgage Amortization Tools')
    parser.add_argument('-i', '--interest', default=6, dest='interest')
    parser.add_argument('-m', '--loan-months', default=None, dest='months')
    parser.add_argument('-a', '--amount', default=100000, dest='amount')
    parser.add_argument('-s', '--summary', default=False, dest='summary')
    parser.add_argument('-f', '--cfile', dest='cfile')
    args = parser.parse_args()

    interest = args.interest
    months = args.months
    amount = args.amount
    value = amount
    down = 0.0
    rent = 0.0
    insurance = 0.0
    taxrate = 0.0
    hoa = 0.0
    expense = 0.0
    rent_increaase_percent = 0.0
    tax_increase_percent = 0.0
    idle_months = 0

    if args.cfile:
        with open(args.cfile) as config_file:
            config = json.load(config_file)
        
        interest = config['interest']
        months = config['months']
        value = config['value']
        down = config['down']
        amount = value - down
        rent = config['rent']
        insurance = config['insurance']
        taxrate = config['taxrate']
        hoa = config['hoa']
        expense = config['expense']
        rent_increase_percent = config['rent-increase-percent']
        tax_increase_percent = config['tax-increase-percent']
        idle_months = config['idle-months']

    r = Rent(rent, insurance, expense, hoa, rent_increase_percent, idle_months)
    m = Mortgage(float(interest) / 100, float(months), amount, value, down, taxrate, tax_increase_percent)

    if args.summary:
        print_summary(m)
    else:
        print_detail(m, r)

if __name__ == '__main__':
    main()
