#include <stdio.h>
#include <string.h>
#include <stdbool.h>
#include <stdlib.h>

#define MAXCHAR 1000
#define MAXSIZE 2484789
#define NBINS 201
#define XMAX 2500
#define XMIN -2500

/* Author: Alexei Chekhlov
   Date: 02/09/2022
   Description: Calculates PDF of 1min data with possible skips given in .csv format */

int main() { 
    FILE *fp, *fp1; 
    char row[MAXCHAR]; 
    char *token; 
    char str[1];
    int OpenPrice, HighPrice, LowPrice, *ClosePrice, Volume, *NumTime; 
    int *NumTimeFilled, *ClosePriceFilled, *DoesPriceExist; 
    char **TextDate, **TextTime, *TextTimeCopy; 
    char *endPtr; 
    int i, j, k, n, SizeFilled;
    int Tau[20];
    int DeltaPrice, DeltaTime; 
    int NumHours, NumMinutes, DaysPassed, PrevNumTime; 
    int *Bin, Dx, **BinCount;
    double **PDF; 

/* time-steps */
    Tau[0] = 1; 
    Tau[1] = 2; 
    Tau[2] = 3; 
    Tau[3] = 6; 
    Tau[4] = 10; 
    Tau[5] = 18; 
    Tau[6] = 32; 
    Tau[7] = 56; 
    Tau[8] = 100; 
    Tau[9] = 178; 
    Tau[10] = 316; 
    Tau[11] = 562; 
    Tau[12] = 1000; 
    Tau[13] = 1778; 
    Tau[14] = 3162; 
    Tau[15] = 5623; 
    Tau[16] = 10000; 
    Tau[17] = 17783; 
    Tau[18] = 31623; 
    Tau[19] = 56234; 

/* memory allocation */
    TextDate = malloc(sizeof(char*)*MAXSIZE); 
    TextTime = malloc(sizeof(char*)*MAXSIZE); 
    TextTimeCopy = malloc(sizeof(char*));
    NumTime = malloc(sizeof(int)*MAXSIZE);
    for (i=0; i<MAXSIZE; i++) {
        TextDate[i] = malloc(sizeof(char*)); 
        TextTime[i] = malloc(sizeof(char*));
    }
    ClosePrice = malloc(sizeof(int)*MAXSIZE);
    Bin = malloc(sizeof(int)*NBINS);
    BinCount = malloc(20*sizeof(int*));
    for (n=0; n<20; n++)
        BinCount[n] = malloc(NBINS*sizeof(int));
    PDF = malloc(20*sizeof(double*));
    for (n=0; n<20; n++)
        PDF[n] = malloc(NBINS*sizeof(double));

/* read the file */
    i = 0; 
    fp = fopen("ES-1min.csv","r");
    fgets(row, MAXCHAR, fp); 
    while ((feof(fp) != true) && (i < MAXSIZE))
    {
        fgets(row, MAXCHAR, fp); 
        token = strtok(row, ","); 
        strcpy(TextDate[i],token); 
        token = strtok(NULL, ","); 
        strcpy(TextTime[i],token); 
        token = strtok(NULL, ","); 
        OpenPrice = (int)(100.0*strtof(token, &endPtr)); 
        token = strtok(NULL, ","); 
        HighPrice = (int)(100.0*strtof(token, &endPtr)); 
        token = strtok(NULL, ","); 
        LowPrice = (int)(100.0*strtof(token, &endPtr));
        token = strtok(NULL, ","); 
        ClosePrice[i] = (int)(100.0*strtof(token, &endPtr)); 
        token = strtok(NULL, ","); 
        Volume = (int)strtof(token, &endPtr); 
        i = i+1;
    }
    fclose(fp);

/* transform text time into numerical time which is equal to 1 at the 1st minute */
    fp = fopen("TimePrice.csv","w"); 
    fprintf(fp,"Time, Price\n"); 
    PrevNumTime = 0; 
    for (i=0; i<MAXSIZE; i++) { 
        strcpy(TextTimeCopy,TextTime[i]); 
        token = strtok(TextTimeCopy,":"); 
        NumHours = (int)strtof(token, &endPtr); 
        token = strtok(NULL, ":"); 
        NumMinutes = (int)strtof(token, &endPtr); 
        NumTime[i] = PrevNumTime+NumHours*60+NumMinutes-8*60-30; 
        if ((i<MAXSIZE-1) && (strcmp(TextDate[i+1],TextDate[i])!=0)) PrevNumTime=NumTime[i]; 
        fprintf(fp,"%d, %d\n", NumTime[i], ClosePrice[i]); 
    } 
    fclose(fp); 

/* fill-in the possible gaps */
    k = -1;
    for (i=0; i<MAXSIZE-1; i++) { // first, determine and allocate the necessary memory
        for (j=NumTime[i]; j<NumTime[i+1]; j++) { 
            k++;
        }
    }
    SizeFilled = k+1;
    NumTimeFilled = malloc(sizeof(int)*SizeFilled);
    ClosePriceFilled = malloc(sizeof(int)*SizeFilled);
    DoesPriceExist = malloc(sizeof(int)*SizeFilled);
    k = -1;
    for (i=0; i<MAXSIZE-1; i++) { // second, fill-in the missing minutes and prices
        for (j=NumTime[i]; j<NumTime[i+1]; j++) {
            k++;
            NumTimeFilled[k] = j;
            ClosePriceFilled[k] = ClosePrice[i];
            if (NumTime[i+1]-NumTime[i]==1) DoesPriceExist[k] = 1;
            else DoesPriceExist[k] = 0;
        }
    }
    fp = fopen("FilledTimePrice.csv","w");
    fprintf(fp,"TimeFilled, PriceFilled\n");
    for (k=0; k<SizeFilled; k++) {
        fprintf(fp,"%d, %d\n",NumTimeFilled[k], ClosePriceFilled[k]);
    }
    fclose(fp);

/* create bins */
    Dx = (int)(XMAX-XMIN)/(NBINS-1);
    printf("Xmax=%d Xmin=%d Nbins=%d Dx=%d\n", XMAX, XMIN, NBINS, Dx); 
    for (n=0; n<NBINS; n++) { 
        Bin[n] = XMIN+Dx*n;
        printf("%d %d\n",n,Bin[n]);
    }
//    scanf("%s",str);

/* PDF calculations */
    for (n=0; n<20; n++) { // steps in time-steps
        for (i=Tau[n]; i<SizeFilled; i++) {
            DeltaPrice = ClosePriceFilled[i] - ClosePriceFilled[i-Tau[n]]; 
//            if (DoesPriceExist[i]==1 && DoesPriceExist[i-Tau[n]]==1) { // use only the real non-filled prices
                if (DeltaPrice < Bin[0]+Dx/2) BinCount[n][0] += 1;
                for (j=1; j<NBINS-1; j++) {
                    if ((DeltaPrice < Bin[j]+Dx/2) && (DeltaPrice >= Bin[j]-Dx/2)) {
                        BinCount[n][j] += 1; 
//                        printf("i=%d P1=%d P2=%d dP=%d j=%d Bin=%d BinCount=%d\n",i,ClosePriceFilled[i],ClosePriceFilled[i-Tau[n]],DeltaPrice,j,Bin[j],BinCount[n][j]);
                    }
                }
                if (DeltaPrice >= Bin[NBINS-1]-Dx/2) BinCount[n][NBINS-1] += 1;
//                scanf("%s",str);
//            }
        }
        for (j=0; j<NBINS; j++) { 
            PDF[n][j] = (double)BinCount[n][j]/((double)(SizeFilled-Tau[n]+1));
        }
    }
    fp = fopen("ProbabilityDensity.csv","w");
    fp1 = fopen("Frequencies.csv","w");
    fprintf(fp,"%s,"," "); // PDF output
    fprintf(fp1,"%s,"," ");
    for (n=0; n<20; n++) {
        fprintf(fp,"%d,",Tau[n]);
        fprintf(fp1,"%d,",Tau[n]);
    }
    fprintf(fp,"\n");
    fprintf(fp1,"\n");
    for (j=0; j<NBINS; j++) {
        fprintf(fp,"%d,",Bin[j]);
        fprintf(fp1,"%d,",Bin[j]);
        for (n=0; n<20; n++) {
            fprintf(fp,"%22.19f,",PDF[n][j]);
            fprintf(fp1,"%d,",BinCount[n][j]);
        }
        fprintf(fp,"\n");
        fprintf(fp1,"\n");
    }
    fclose(fp);
    fclose(fp1);

    return 0;
}
