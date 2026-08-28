function Price= BlackScholesStocks(callput, S,K,r,sigma,T)
 
d1 = (log(S/K) + (r + 0.5*sigma^2)*T)/(sigma*sqrt(T));
d2 = d1 - sigma*sqrt(T);

if callput=='c'   
    %for call
    N1 =  normcdf(d1); %also N(d1)=0.5*(1+erf(d1/sqrt(2)));
    N2 =  normcdf(d2);

    Price = S*N1-K*exp(-r*T)*N2;
else
    if callput=='p'
    % for put

     N1 =  normcdf(-d1); %also N(d1)=0.5*(1+erf(d1/sqrt(2)));
     N2 =  normcdf(-d2);

    Price = K*exp(-r*T)*N2 - S*N1;
    end
end
end