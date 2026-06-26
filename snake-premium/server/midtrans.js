const midtransClient = require('midtrans-client');

const snap = new midtransClient.Snap({
  isProduction: false,
  serverKey: process.env.MIDTRANS_SERVER_KEY,
  clientKey: process.env.MIDTRANS_CLIENT_KEY
});

async function createTransaction(orderId, grossAmount) {
  const parameter = {
    transaction_details: {
      order_id: orderId,
      gross_amount: grossAmount
    },
    credit_card: {
      secure: true
    },
    enabled_payments: ['gopay'],
    callbacks: {
      finish: 'http://localhost:3000/payment-finish'
    }
  };

  const transaction = await snap.createTransaction(parameter);
  return {
    token: transaction.token,
    redirectUrl: transaction.redirect_url
  };
}

async function verifyNotification(orderId) {
  const statusResponse = await snap.transaction.status(orderId);
  return {
    orderId: statusResponse.order_id,
    transactionStatus: statusResponse.transaction_status,
    paymentType: statusResponse.payment_type,
    grossAmount: statusResponse.gross_amount
  };
}

module.exports = { createTransaction, verifyNotification };
