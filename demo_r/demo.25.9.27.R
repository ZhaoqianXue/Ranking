library(readr)
library(dplyr)

### generate data for testing ###
set.seed(1)

n <- 1000   # there are n samples
k <- 5     # there are k methods
na_frac <- 0.05  # there are 5% of NA`s 
rankings <- 1:5  
variances <- rep(0.5, k)
data <- matrix(nrow = n, ncol = k)

for (j in 1:k) {
  data[, j] <- rnorm(n, mean = rankings[j], sd = sqrt(variances[j]))
}
na_idx <- sample(length(data), size = floor(na_frac * length(data)))
data[na_idx] <- NA
df <- as.data.frame(data)
colnames(df) <- paste0("Method", 1:k)

write.csv(df, file.path(getwd(), "simulated_data.csv"), row.names = FALSE)
head(data)


### Process data ###
process_data <- function(data, bigbetter = FALSE) {

  Idx <- colnames(data)
  numidx <- length(Idx)
  xx = matrix(0,0,numidx)
  ww = matrix(0,0,numidx)
  count <- 0
  
  ### iterate each sample to create graph ###
  for (i in 1:nrow(data)){
    target_row <- data[i, ]
    
    pairs <- t(combn(seq_along(target_row), 2))
    valid_idx <- !is.na(target_row[pairs[,1]]) & !is.na(target_row[pairs[,2]])
    pairs <- pairs[valid_idx, , drop = FALSE]
    
    if (bigbetter) {
      v1 <- ifelse(target_row[pairs[,1]] > target_row[pairs[,2]], Idx[pairs[,2]], Idx[pairs[,1]])
      v2 <- ifelse(target_row[pairs[,1]] > target_row[pairs[,2]], Idx[pairs[,1]], Idx[pairs[,2]])
    } else {
      v1 <- ifelse(target_row[pairs[,1]] > target_row[pairs[,2]], Idx[pairs[,1]], Idx[pairs[,2]])
      v2 <- ifelse(target_row[pairs[,1]] > target_row[pairs[,2]], Idx[pairs[,2]], Idx[pairs[,1]])
    }
    
    tmp.xx <- matrix(0, nrow = length(v1), ncol = numidx)
    tmp.ww <- matrix(0, nrow = length(v1), ncol = numidx)
  
    for (i in seq_along(v1)) {
      tmp.xx[i, Idx == v1[i]] <- 1
      tmp.xx[i, Idx == v2[i]] <- 1
      tmp.ww[i, Idx == v2[i]] <- 1
    }
    xx <- rbind(xx, tmp.xx)
    ww <- rbind(ww, tmp.ww)
    
    count <- count + length(v1)
  }
  
  yy <- matrix(c(xx), ncol = numidx)
  zz <- matrix(c(ww), ncol = numidx)
  
  AA2 = as.matrix(yy)
  WW2 = as.matrix(zz)
  return(list(aa = AA2, ww = WW2, idx=Idx))
}

### Vanilla spectral method ###
vanilla_spectrum_method <- function(AA2, WW2, Idx) {
  
  B = 2000
  n = ncol(AA2)
  L2 = nrow(AA2)
  fAvec2 = numeric(L2)+2                                                 ## weight for vanilla spectral method ##

  ##-----------------------------------------------------------------    ## compute matrix P ##
  dval2 = 2*max(colSums(AA2))                                         
  P2 = matrix(0,n,n)
  for(i in 1:n){
  	for(j in 1:n){
  		if(j != i){
  			P2[i,j] = sum(AA2[,i]*AA2[,j]*WW2[,j]/fAvec2)/dval2        
  		}
  	}
  	P2[i,i] = 1-sum(P2[i,])
  }
  
  ##-----------------------------------------------------------------    ## solve theta and pi ##
  tmp.P2 = t(t(P2)-diag(n))%*%(t(P2)-diag(n))
  tmp.svd2 = svd(tmp.P2)
  pihat2 = abs(tmp.svd2$v[,n])
  thetahat2 = log(pihat2)-mean(log(pihat2))
  
  ##-----------------------------------------------------------------    ## output ##
  RR2 = matrix(0,6,n)
  colnames(RR2) <- Idx
  RR2[1,] = thetahat2
  RR2[2,] = n+1-rank(thetahat2) 
Vmatrix2 = matrix(0,L2,n)
tauhatvec2 = numeric(n)
tmp.pimatrix2 = t(AA2)*pihat2
tmp.pivec2 = colSums(tmp.pimatrix2)
tmp.var2 = numeric(n)

for(oo in 1:n){
	tauhatvec2[oo] = sum(AA2[,oo]*(1-pihat2[oo]/tmp.pivec2)*pihat2[oo]/fAvec2, na.rm = TRUE)/dval2
	tmp.var2[oo] = sum(AA2[,oo]*(tmp.pivec2-pihat2[oo])/fAvec2/fAvec2)*pihat2[oo]/dval2/dval2/tauhatvec2[oo]/tauhatvec2[oo]
	Vmatrix2[,oo] = (AA2[,oo]*WW2[,oo]*tmp.pivec2-AA2[,oo]*pihat2[oo])/fAvec2  
}
sigmahatmatrix2 = matrix(tmp.var2,n,n)+t(matrix(tmp.var2,n,n))

##-----------------------------------------------------------------    ## Weighted bootstrap ##
Wmatrix2 = matrix(rnorm(L2*B),L2,B)
tmp.Vtau2 = (t(Vmatrix2)/tauhatvec2)%*%Wmatrix2

R.left.m2 = numeric(n)
R.right.m2 = numeric(n)
R.left.one.m2 = numeric(n)

for(ooo in 1:n){
	tmpGMmatrix02 = matrix(rep(tmp.Vtau2[ooo,],n)-c(t(tmp.Vtau2)),B,n)
	tmpGMmatrix2 = abs(t(t(tmpGMmatrix02)/sqrt(sigmahatmatrix2[ooo,]))/dval2)
	tmpGMmatrixone2 = t(t(tmpGMmatrix02)/sqrt(sigmahatmatrix2[ooo,]))/dval2
	tmp.GMvecmax2 = apply(tmpGMmatrix2,1,max)
	tmp.GMvecmaxone2 = apply(tmpGMmatrixone2,1,max)
    cutval2 = quantile(tmp.GMvecmax2,0.95)
    cutvalone2 = quantile(tmp.GMvecmaxone2,0.95)
	tmp.theta.sd2 = sqrt(sigmahatmatrix2[ooo,])
	tmp.theta.sd2 = tmp.theta.sd2[-ooo]
	R.left.m2[ooo] = 1+sum(1*(((thetahat2[-ooo]-thetahat2[ooo])/tmp.theta.sd2)>cutval2))
	R.right.m2[ooo] = n-sum(1*(((thetahat2[-ooo]-thetahat2[ooo])/tmp.theta.sd2)<(-cutval2)))
	R.left.one.m2[ooo] = 1+sum(1*(((thetahat2[-ooo]-thetahat2[ooo])/tmp.theta.sd2)>cutvalone2))
}

RR2[3,] = R.left.m2    ## two-sided CI for rank ##
RR2[4,] = R.right.m2
RR2[5,] = R.left.one.m2 ## left-sided CI for rank ##

## -----------------------------------------------------------------    ## Weighted bootstrap ##
Wmatrix2 <- matrix(rnorm(L2 * B), L2, B)
tmp.Vtau2 <- (t(Vmatrix2) / tauhatvec2) %*% Wmatrix2
Mval <- n
GMvecmax2 <- numeric(B) - 1
GMvecmaxone2 <- numeric(B) - Inf
tmpTMval2 <- -1
tmpTMvalone2 <- -Inf
for (ooo in 1:n) {
  tmpGMmatrix02 <- matrix(rep(tmp.Vtau2[ooo, ], n) - c(t(tmp.Vtau2)), B, n)
  tmpGMmatrix2 <- abs(t(t(tmpGMmatrix02) / sqrt(sigmahatmatrix2[ooo, ])) / dval2)
  tmpGMmatrixone2 <- t(t(tmpGMmatrix02) / sqrt(sigmahatmatrix2[ooo, ])) / dval2
  tmp.GMvecmax2 <- apply(tmpGMmatrix2, 1, max)
  tmp.GMvecmaxone2 <- apply(tmpGMmatrixone2, 1, max)
  GMvecmax2 <- c(GMvecmax2, tmp.GMvecmax2)
  GMvecmaxone2 <- c(GMvecmaxone2, tmp.GMvecmaxone2)
}
GMmaxmatrixone2 <- matrix(GMvecmaxone2, B)
GMmaxone2 <- apply(GMmaxmatrixone2, 1, max)
cutvalone2 <- quantile(GMmaxone2, 0.95)
R.left.one2 <- numeric(n)
for (oooo in 1:n) {
  tmp.theta.sd2 <- sqrt(sigmahatmatrix2[oooo, ])
  tmp.theta.sd2 <- tmp.theta.sd2[-oooo]
  R.left.one2[oooo] <- 1 + sum(1 * (((thetahat2[-oooo] - thetahat2[oooo]) / tmp.theta.sd2) > cutvalone2))
}

RR2[6, ] <- R.left.one2 ## uniform left-sided CI for rank ##
rownames(RR2) <- c("theta.hat", "Ranking", "two-sided CI", "two-sided CI", "left-sided CI", "uniform left-sided CI")
return(RR2)
}

### test on generated data ###
data <- read_csv(file.path(getwd(), "simulated_data.csv"), show_col_types = FALSE)

data <- process_data(data)
rr <- vanilla_spectrum_method(data$aa, data$ww, data$idx)
print(rr)
### test on real PRS AoU ensemble data ###
data <- read_csv(file.path(getwd(), "top2000childrencode_report_aou.csv"), show_col_types = FALSE)
data <- data %>% select(-case_num, -model, -description)

data <- process_data(data, bigbetter = TRUE)
rr <- vanilla_spectrum_method(data$aa, data$ww, data$idx)
print(rr)

### test on real PRS UKBB ensemble data ###
data <- read_csv(file.path(getwd(), "top2000childrencode_report_ukbb.csv"), show_col_types = FALSE)
data <- data %>% select(-case_num, -model, -description)

data <- process_data(data, bigbetter = TRUE)
rr <- vanilla_spectrum_method(data$aa, data$ww, data$idx)
print(rr)
