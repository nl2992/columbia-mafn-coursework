
clear all, clc;

%variables initialization
dataFile='HO-5minHLV.csv';

inSample=[datenum('01/01/1980'),datenum('01/01/2000')];
outSample=[datenum('01/01/2000'),datenum('03/23/2023')];

barsBack=17001;
slpg=47;
PV=42000;

% 11500 0.019
% 12700 0.01
Length=12700:100:12700;
StopPct=0.010:0.001:0.010;

resultLabel={'Profit','WorstDrawDown','StDev','#trades'};

resultInSample=zeros(length(Length),length(StopPct),length(resultLabel));
resultOutSample=zeros(length(Length),length(StopPct),length(resultLabel));

E0=100000;

trades=[];
limitBuy=nan;
limitSell=nan;
stopOrder=nan;
position=0;

%uploading data
d=ezread(dataFile);
d.numTime=datenum(d.Time);
d.numTime=datenum(d.Date)+d.numTime-floor(d.numTime);
d.N=length(d.numTime);
d.M=5;

figure(1); clf(1); plot(d.numTime,d.Close,'b'); datetick('x');
%return;

%index for in-Sample:
indInSample1=max(sum(d.numTime<inSample(1))+1,barsBack);
indInSample2=max(sum(d.numTime<(inSample(2)+1)),barsBack);

%index for out-of-Sample:
indOutSample1=max(sum(d.numTime<outSample(1))+1,barsBack);
indOutSample2=max(sum(d.numTime<(outSample(2)+1)),barsBack);



%calculating the statistics

for i=1:length(Length)
    L=Length(i);
    disp(['calculating for Length = ' num2str(L)]);
    
    %we can calculate HH and LL for all StopPct with the same Length
    HH=zeros(length(d.numTime),1);
    LL=zeros(length(d.numTime),1);
    
    for k=(barsBack+1):length(d.numTime)
        HH(k)=max(d.High((k-L):(k-1)));
        LL(k)=min(d.Low((k-L):(k-1)));
    end
    
    for j=1:length(StopPct)
        S=StopPct(j);
        %disp(['calculating for StopPct = ' num2str(S)]);
        
        %setting initial conditions:
        limitBuy=nan;
        limitSell=nan;
        stopOrder=nan;
        
        position=0;
        E=zeros(length(d.numTime),1)+E0;
        DD=zeros(length(d.numTime),1);
        trades=zeros(length(d.numTime),1);
        Emax=E0;
        
        %running through the time and trading:
        for k=(barsBack+1):length(d.numTime)
            traded=false;
            delta=PV*(d.Close(k)-d.Close(k-1))*position;
            
            if (position== 0)
                 
                buy=d.High(k)>=HH(k);
                sell=d.Low(k)<=LL(k);
                
                if (buy && sell)
                   delta = -slpg+PV*(LL(k)-HH(k));
                   trades(k)=1;
                else
                    if(buy)
                        delta = -slpg/2 + PV*(d.Close(k)-HH(k));
                        position= 1;
                        traded=true;
                        benchmarkLong=d.High(k);
                        trades(k)=0.5;
                    end
                    if(sell)
                        delta = -slpg/2 - PV*(d.Close(k)-LL(k));
                        position=-1;
                        traded=true;
                        benchmarkShort=d.Low(k);
                        trades(k)=0.5;
                    end
                end
                
            end
            
            if (position== 1 && ~traded) 
                sellShort=d.Low(k)<=LL(k);
                sell=d.Low(k)<=(benchmarkLong*(1-S));
                
                if(sellShort && sell)
                    %copy of sell short
                    if(sellShort)
                        delta=delta-slpg-2*PV*(d.Close(k)-LL(k));
                        position=-1;
                        benchmarkShort=d.Low(k);
                        trades(k)=1;
                    end
                
                else
                    if(sell)
                        delta=delta-slpg/2-PV*(d.Close(k)-(benchmarkLong*(1-S)));%min(Open,stopPrice)
                        position=0;
                        trades(k)=0.5;
                    end
                    
                    if(sellShort)
                        delta=delta-slpg-2*PV*(d.Close(k)-LL(k));%min(Open,LL(k))
                        position=-1;
                        benchmarkShort=d.Low(k);
                        trades(k)=1;
                    end
                end
                
                benchmarkLong=max(d.High(k),benchmarkLong);
                
            end
            
            if (position==-1 && ~traded)
                buyLong=d.High(k)>=HH(k);
                buy=d.High(k)>=(benchmarkShort*(1+S));
                
                if(buyLong && buy)
                    %copy of buyLong
                    if(buyLong)
                        delta=delta-slpg+2*PV*(d.Close(k)-HH(k));
                        position=1;
                        benchmarkLong=d.High(k);
                        trades(k)=1;
                    end
                
                else
                    if(buy)
                        delta=delta-slpg/2+PV*(d.Close(k)-(benchmarkShort*(1+S)));
                        position=0;
                        trades(k)=0.5;
                    end
                    
                    if(buyLong)
                        delta=delta-slpg+2*PV*(d.Close(k)-HH(k));
                        position=1;
                        benchmarkLong=d.High(k);
                        trades(k)=1;
                    end
                end
                
                benchmarkShort=min(d.Low(k),benchmarkShort);
            end
            
            if (position== 0 && traded),  end
            
            if (position== 1 && traded),  end
            
            if (position==-1 && traded),  end
            
            %update equity
            E(k)=E(k-1)+delta; 
            %calculate drawdown
            Emax=max(Emax, E(k));
            DD(k)=E(k)-Emax;
        end
        
        %calculate statistics for the Equity curve
        %ProfitAndLoss calculation
        PnL=[zeros(barsBack,1); E((barsBack+1):end)-E(barsBack:(end-1))];
        %for in-Sample:
        resultInSample(i,j,:)=[E(indInSample2)-E(indInSample1),min(DD(indInSample1:indInSample2)),std(PnL(indInSample1:indInSample2)),sum(trades(indInSample1:indInSample2))]; %{'Profit','WorstDrawDown','StDev','#trades'}

        %index for out-of-Sample:
        resultOutSample(i,j,:)=[E(indOutSample2)-E(indOutSample1),min(DD(indOutSample1:indOutSample2)),std(PnL(indOutSample1:indOutSample2)),sum(trades(indOutSample1:indOutSample2))]; %{'Profit','WorstDrawDown','StDev','#trades'}
        
        disp([num2str(S) ': in/out: ' num2str(resultInSample(i,j,:)) ' / ' num2str(resultOutSample(i,j,:))]);
    end
end


ind=(indOutSample1:indOutSample2);figure(2); clf(2); X=[d.Open(ind), d.High(ind), d.Low(ind), d.Close(ind)];  
%highlow(X,'b'); 
hold on; plot(HH(ind),'g'); plot(HH(ind)*(1-S),'--g'); plot(LL(ind),'c'); plot(LL(ind)*(1+S),'--c'); plot((0.5./trades(ind)).*HH(ind),'.r');plot((0.5./trades(ind)).*LL(ind),'.r'); plot((0.5./trades(ind)).*HH(ind)*(1-S),'.r'); plot((0.5./trades(ind)).*LL(ind)*(1+S),'.r'); plot((trades(ind))*4+2,'--r'); hold off;

ind=(indOutSample1:indOutSample2);figure(3); clf(3); T=datetime(d.numTime(ind),'ConvertFrom','datenum'); X=[d.Open(ind), d.High(ind), d.Low(ind), d.Close(ind)]; 
%TT = array2timetable(X,'RowTimes',T,'VariableNames',{'open','high','low','close'}); 
%highlow(TT,'b'); 
hold on; plot(T,HH(ind),'g'); plot(T,HH(ind)*(1-S),'--g'); plot(T,LL(ind),'c'); plot(T,LL(ind)*(1+S),'--c'); plot(T,(0.5./trades(ind)).*HH(ind),'.r');plot(T,(0.5./trades(ind)).*LL(ind),'.r'); plot(T,(0.5./trades(ind)).*HH(ind)*(1-S),'.r'); plot(T,(0.5./trades(ind)).*LL(ind)*(1+S),'.r'); plot(T,(trades(ind))*4+2,'--r'); hold off;

ind=(indOutSample1:indOutSample2);figure(4); clf(4); 
hold on; plot(E(ind),'g'); hold off;

ind=(indOutSample1:indOutSample2);figure(4); clf(4); 
hold on; plot(E(ind),'g'); hold off;
