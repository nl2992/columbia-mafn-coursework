%This script plots graph of BlackScholes call as a function
%of stock price
%It uses function BlackScholesStocks('c',X,Strike,Rate,Volatility,Time);
%That function is defined in file BlackScholesStocks.m


clear all
%parameters

dx=0.1; %step to evaluate option for graphing
maxX=20; %max value of Stock price on graph

X=dx:dx:maxX; %array of stock prices for which we calculate call price

Strike=10;
Rate=0.01;
Time=1;
Volatility=0.3;

Y=max(X-Strike,0); %array of Call payoff at expiration 
i=0;
for X=dx:dx:maxX;
  i=i+1;
  Z(i)=BlackScholesStocks('c',X,Strike,Rate,Volatility,Time);
end

X=dx:dx:maxX;

plot(X,Z, X,Y);