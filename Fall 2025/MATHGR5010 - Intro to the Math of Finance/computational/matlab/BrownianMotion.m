%Matlab c style code for Brownian Motion
%matlab has an imbedded functions for Brownian Motion.
%It is also possible to
%neatly write in Matlab a 4 liner:

% N = 1000;
% dW = randn(1,N);
% x = cumsum(dW);
% plot(x);

%However we resort to a slow
%c style code with loops for educational purposes

M=10000; %number of trajectories of Brownian motion
N=250;%Number of steps in one trajectory
X0=0; %initial point
T=1;  %Final Time in years in trajectory

dt=T/N; %time step
Sqrtdt=sqrt(dt);

%X(j,:) j-th trajectory of Brownian Motion
X(1:M,1)=X0; % Initial value of Brownian Motion  X(j,1)=X0 for all j=1:M
             %here index starts with 1 and not 0 as in Matlab array index should be
             %positive
for j=1:M  %generate M trajectories
    for i = 2:N+1  %generate j-th trajectory
        X(j,i)=X(j,i-1)+Sqrtdt*randn;    
    end
end

t=0:dt:T;
plot(t,X(:,:));


