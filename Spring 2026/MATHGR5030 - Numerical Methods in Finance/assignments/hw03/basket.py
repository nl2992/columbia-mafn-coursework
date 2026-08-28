# -*- coding: utf-8 -*-
"""
Created on Tue Sep 19 22:56:58 2017

@author: jaehyuk
"""
import numpy as np
import scipy.stats as ss

def basket_check_args(spot, vol, corr_m, weights):
    '''
    This function simply checks that the size of the vector (matrix) are consistent
    '''
    n = spot.size
    assert( n == vol.size )
    assert( corr_m.shape == (n, n) )
    return None
    
def basket_price_mc_cv(
    strike, spot, vol, weights, texp, cor_m, 
    intr=0.0, divr=0.0, cp=1, n_samples=10000,
    rng = None
):
    if rng is None:
        rng = np.random.default_rng()
    # price1 = MC based on BSM
    
    state = rng.bit_generator.state # Store random state first
    price1 = basket_price_mc(
        strike, spot, vol, weights, texp, cor_m,
        intr, divr, cp, True, n_samples,
        rng = rng
    )
    
    ''' 
    compute price2: mc price based on Bachelier model
    make sure you use the same seed

    # Restore the state in order to generate the same state
    rng.bit_generator.state = state
    price2 = basket_price_mc(
        strike, spot, spot*vol, weights, texp, cor_m,
        intr, divr, cp, False, n_samples
        rng = rng
    )
    '''
    price2 = 0

    ''' 
    compute price3: analytic price based on Bachelier model
    
    price3 = basket_price_norm_analytic(
        strike, spot, vol, weights, texp, cor_m, intr, divr, cp)
    '''
    price3 = 0
    
    # return two prices: without and with CV
    return np.array([price1, price1 - (price2 - price3)])


def basket_price_mc(
    strike, spot, vol, weights, texp, cor_m,
    intr=0.0, divr=0.0, cp=1, bsm=True, n_samples = 100000,
    rng=None
):
    basket_check_args(spot, vol, cor_m, weights)
    
    div_fac = np.exp(-texp*divr)
    disc_fac = np.exp(-texp*intr)
    forward = spot / disc_fac * div_fac

    cov_m = vol * cor_m * vol[:,None]
    chol_m = np.linalg.cholesky(cov_m)  # L matrix in slides

    n_assets = spot.size
    if rng is None:
        rng = np.random.default_rng()
        
    znorm_m = rng.standard_normal(size=(n_samples, n_assets))
    
    if( bsm ) :
        '''
        PUT the simulation of the geometric Brownian motion below
        '''
        prices = np.zeros_like(znorm_m)
    else:
        # Bachelier Model (bsm = False)
        prices = forward + np.sqrt(texp) * znorm_m @ chol_m.T
    
    price_weighted = np.inner(prices, weights)
    
    price = np.mean( np.fmax(cp*(price_weighted - strike), 0) )
    return disc_fac * price


def basket_price_norm_analytic(
    strike, spot, vol, weights, 
    texp, cor_m, intr=0.0, divr=0.0, cp=1
):
    
    '''
    The analytic (exact) option price under the normal model
    
    1. compute the forward of the basket
    2. compute the normal volatility of basket
    3. plug in the forward and volatility to the normal price formula
    
    PUT YOUR CODE BELOW
    '''
    
    return 0.0
